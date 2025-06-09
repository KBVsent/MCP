import os
import subprocess
import json
import threading
import queue
import time
from rich import print
from dotenv import load_dotenv
import anthropic
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import confirm

load_dotenv()

api_key = os.environ.get("ANTHROPIC_API_KEY")
print(f"API Key loaded: {api_key[:10]}..." if api_key else "No API Key found")

# 初始化 Anthropic 客户端
client = anthropic.Anthropic(api_key=api_key)

class MCPStdioClient:
    """本地 STDIO MCP 客户端"""
    
    def __init__(self, server_script_path, cwd=None):
        self.server_script_path = server_script_path
        self.cwd = cwd or os.getcwd()
        self.process = None
        self.tools = []
        self.response_queue = queue.Queue()
        self.stderr_queue = queue.Queue()
        self.request_id = 0
    
    def start_server(self):
        """启动 MCP 服务器进程"""
        try:
            self.process = subprocess.Popen(
                ["python", self.server_script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.cwd,
                env=dict(os.environ),
                bufsize=0  # 无缓冲
            )
            
            # 启动后台线程读取输出
            self._start_reader_threads()
            
            print(f"[green]✅ MCP 服务器已启动 (PID: {self.process.pid})[/green]")
            return True
        except Exception as e:
            print(f"[red]❌ 启动 MCP 服务器失败: {e}[/red]")
            return False
    
    def _start_reader_threads(self):
        """启动后台线程读取 stdout 和 stderr"""
        def read_stdout():
            while self.process and self.process.poll() is None:
                try:
                    line = self.process.stdout.readline()
                    if line:
                        print(f"📥 收到服务器响应: {line.strip()}")
                        try:
                            response = json.loads(line.strip())
                            self.response_queue.put(response)
                        except json.JSONDecodeError as e:
                            print(f"⚠️ JSON 解析错误: {e}, 原始数据: {line.strip()}")
                except Exception as e:
                    print(f"❌ 读取 stdout 错误: {e}")
                    break
        
        def read_stderr():
            while self.process and self.process.poll() is None:
                try:
                    line = self.process.stderr.readline()
                    if line:
                        error_msg = line.strip()
                        # 区分日志级别，只有真正的错误才标记为错误
                        if any(level in error_msg.upper() for level in ['ERROR', 'CRITICAL', 'FATAL']):
                            print(f"[red]🔴 MCP 服务器错误: {error_msg}[/red]")
                            self.stderr_queue.put(error_msg)
                        elif any(level in error_msg.upper() for level in ['WARN', 'WARNING']):
                            print(f"[yellow]⚠️ MCP 服务器警告: {error_msg}[/yellow]")
                        elif any(level in error_msg.upper() for level in ['INFO', 'DEBUG']):
                            print(f"ℹ️ MCP 服务器信息: {error_msg}")
                        else:
                            # 对于无法识别级别的消息，保持谨慎，仍标记为错误
                            print(f"[yellow]🔴 MCP 服务器输出: {error_msg}[/yellow]")
                            self.stderr_queue.put(error_msg)
                except Exception as e:
                    print(f"[red]❌ 读取 stderr 错误: {e}[/red]")
                    break
        
        # 启动后台线程
        threading.Thread(target=read_stdout, daemon=True).start()
        threading.Thread(target=read_stderr, daemon=True).start()
    
    def send_request(self, method, params=None, timeout=10):
        """发送请求并等待响应，支持超时"""
        if not self.process:
            raise Exception("MCP 服务器未启动")
        
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
        
        try:
            # 发送请求
            request_json = json.dumps(request) + "\n"
            print(f"📤 发送请求: {method}")
            print(f"📝 请求内容: {request_json.strip()}")
            
            self.process.stdin.write(request_json)
            self.process.stdin.flush()
            
            # 等待响应（带超时）
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    response = self.response_queue.get(timeout=1)
                    if response.get("id") == self.request_id:
                        print(f"✅ 收到匹配响应: {response}")
                        return response
                    else:
                        # 如果 ID 不匹配，放回队列
                        self.response_queue.put(response)
                except queue.Empty:
                    continue
            
            # 超时处理
            print(f"[red]⏰ 请求超时 ({timeout}秒): {method}[/red]")
            
            # 检查是否有错误信息
            error_messages = []
            try:
                while True:
                    error_msg = self.stderr_queue.get_nowait()
                    error_messages.append(error_msg)
            except queue.Empty:
                pass
            
            if error_messages:
                print(f"[red]🔴 发现错误信息: {error_messages}[/red]")
            
            return None
            
        except Exception as e:
            print(f"❌ 发送请求失败: {e}")
            return None
    
    def initialize(self):
        """初始化 MCP 连接"""
        print("🔄 开始初始化 MCP 连接...")
        
        response = self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {}
            },
            "clientInfo": {
                "name": "anime-calendar-client",
                "version": "1.0.0"
            }
        })
        
        if response and "error" not in response:
            print("[green]✅ MCP 连接初始化成功[/green]")
            
            # 发送 initialized 通知
            initialized_request = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            request_json = json.dumps(initialized_request) + "\n"
            self.process.stdin.write(request_json)
            self.process.stdin.flush()
            print("📤 已发送 initialized 通知")
            
            return True
        else:
            print(f"❌ MCP 初始化失败: {response}")
            return False
    
    def list_tools(self):
        """获取可用工具列表"""
        print("🔄 正在获取工具列表...")
        
        response = self.send_request("tools/list", timeout=15)
        
        if response and "result" in response:
            self.tools = response["result"].get("tools", [])
            print(f"✅ 获取到 {len(self.tools)} 个工具:")
            for tool in self.tools:
                print(f"  - {tool['name']}: {tool.get('description', '无描述')}")
            return self.tools
        elif response and "error" in response:
            print(f"❌ 服务器返回错误: {response['error']}")
            return []
        else:
            print("❌ 获取工具列表失败或超时")
            print("🔍 请检查您的 mcp_server.py 是否正确实现了 tools/list 方法")
            
            # 尝试直接测试服务器响应
            print("\n🧪 尝试发送简单的测试请求...")
            test_response = self.send_request("ping", {}, timeout=5)
            if test_response:
                print(f"✅ 服务器响应测试请求: {test_response}")
            else:
                print("❌ 服务器未响应测试请求")
            
            return []
    
    def call_tool(self, tool_name, arguments=None):
        """调用指定工具"""
        print(f"🔧 调用工具: {tool_name}")
        print(f"📝 工具参数: {arguments}")
        
        response = self.send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments or {}
        })
        
        if response and "result" in response:
            print(f"✅ 工具执行成功: {response['result']}")
            return response["result"]
        else:
            print(f"❌ 工具调用失败: {response}")
            return None
    
    def stop_server(self):
        """停止 MCP 服务器"""
        if self.process:
            print("🔄 正在停止 MCP 服务器...")
            self.process.terminate()
            self.process.wait()
            print("✅ MCP 服务器已停止")
    
    def debug_info(self):
        """输出调试信息"""
        print("\n🔍 调试信息:")
        print(f"服务器进程状态: {'运行中' if self.process and self.process.poll() is None else '已停止'}")
        print(f"响应队列大小: {self.response_queue.qsize()}")
        print(f"错误队列大小: {self.stderr_queue.qsize()}")

def create_anthropic_tools_from_mcp(mcp_tools):
    """将 MCP 工具转换为 Anthropic API 格式"""
    anthropic_tools = []
    for tool in mcp_tools:
        anthropic_tool = {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "input_schema": tool.get("inputSchema", {"type": "object", "properties": {}})
        }
        anthropic_tools.append(anthropic_tool)
    return anthropic_tools

def query_with_mcp_tools(query, mcp_client, conversation_history=None):
    """使用 MCP 工具进行查询，支持多轮对话和流式输出"""
    print(f"\n🤖 开始处理查询: {query}")
    
    # 如果没有提供对话历史，创建新的
    if conversation_history is None:
        conversation_history = []
    
    try:
        # 获取 MCP 工具并转换格式
        mcp_tools = mcp_client.tools
        if not mcp_tools:
            print("❌ 没有可用的 MCP 工具")
            return None, conversation_history
        
        anthropic_tools = create_anthropic_tools_from_mcp(mcp_tools)
        print(f"🔧 转换了 {len(anthropic_tools)} 个工具供 Claude 使用")
        
        # 构建包含历史对话的消息列表
        messages = conversation_history.copy()
        messages.append({"role": "user", "content": query})
        
        # 调用 Claude API（流式）
        print("📞 正在调用 Claude API...")
        print("\n💬 Claude 回复:")
        print("-" * 40)
        
        # 使用流式 API
        response_stream = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=messages,
            tools=anthropic_tools,
            stream=True
        )
        
        # 处理流式响应
        assistant_content = []
        current_text = ""
        current_tool_use = None
        
        for chunk in response_stream:
            print(f"[blue]{chunk}[/blue]")
            if chunk.type == "message_start":
                continue
            elif chunk.type == "content_block_start":
                if chunk.content_block.type == "text":
                    # 开始新的文本块
                    pass
                elif chunk.content_block.type == "tool_use":
                    # 开始新的工具使用块
                    current_tool_use = {
                        "type": "tool_use",
                        "id": chunk.content_block.id,
                        "name": chunk.content_block.name,
                        "input": {}
                    }
            elif chunk.type == "content_block_delta":
                if chunk.delta.type == "text_delta":
                    # 流式文本输出
                    text_delta = chunk.delta.text
                    current_text += text_delta
                    print(text_delta, end="", flush=True)
                elif chunk.delta.type == "input_json_delta":
                    # 工具参数的增量更新
                    if current_tool_use:
                        # 累积工具参数
                        if 'input_json' not in current_tool_use:
                            current_tool_use['input_json'] = ""
                        current_tool_use['input_json'] += chunk.delta.partial_json
            elif chunk.type == "content_block_stop":
                if current_text:
                    # 文本块结束，添加到内容中
                    assistant_content.append({
                        "type": "text",
                        "text": current_text
                    })
                    current_text = ""
                elif current_tool_use:
                    # 工具使用块结束，解析参数
                    try:
                        if 'input_json' in current_tool_use:
                            current_tool_use['input'] = json.loads(current_tool_use['input_json'])
                            del current_tool_use['input_json']
                        assistant_content.append(current_tool_use)
                        current_tool_use = None
                    except json.JSONDecodeError as e:
                        print(f"\n❌ 工具参数解析错误: {e}")
            elif chunk.type == "message_stop":
                break
        
        print("\n" + "-" * 40)
        print("✅ Claude API 调用完成")
        
        # 处理工具调用
        has_tool_calls = any(content.get('type') == 'tool_use' for content in assistant_content)
        
        if has_tool_calls:
            # 先添加助手的回复（包含工具调用）
            messages.append({"role": "assistant", "content": assistant_content})
            
            # 处理每个工具调用
            tool_results = []
            for content in assistant_content:
                if content.get('type') == 'tool_use':
                    tool_name = content['name']
                    tool_args = content['input']
                    tool_use_id = content['id']
                    
                    print(f"\n🔧 Claude 要求调用工具: {tool_name}")
                    print(f"📝 工具参数: {tool_args}")
                    
                    # 调用 MCP 工具
                    tool_result = mcp_client.call_tool(tool_name, tool_args)
                    
                    if tool_result:
                        print(f"✅ 工具执行结果: {tool_result}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": json.dumps(tool_result, ensure_ascii=False)
                        })
                    else:
                        print("❌ 工具执行失败")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": "工具执行失败"
                        })
            
            # 添加工具结果消息
            if tool_results:
                messages.append({
                    "role": "user", 
                    "content": tool_results
                })
                
                # 将工具结果返回给 Claude（流式）
                print("📞 将工具结果返回给 Claude...")
                print("\n🎯 Claude 最终回复:")
                print("-" * 40)
                
                follow_up_stream = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2000,
                    messages=messages,
                    tools=anthropic_tools,
                    stream=True
                )
                
                final_assistant_content = []
                final_text = ""
                
                for chunk in follow_up_stream:
                    if chunk.type == "content_block_start":
                        if chunk.content_block.type == "text":
                            pass
                    elif chunk.type == "content_block_delta":
                        if chunk.delta.type == "text_delta":
                            text_delta = chunk.delta.text
                            final_text += text_delta
                            print(text_delta, end="", flush=True)
                    elif chunk.type == "content_block_stop":
                        if final_text:
                            final_assistant_content.append({
                                "type": "text",
                                "text": final_text
                            })
                            final_text = ""
                    elif chunk.type == "message_stop":
                        break
                
                print("\n" + "-" * 40)
                
                # 更新对话历史（包含最终回复）
                messages.append({"role": "assistant", "content": final_assistant_content})
        else:
            # 如果没有工具调用，直接更新对话历史
            messages.append({"role": "assistant", "content": assistant_content})
        
        return True, messages  # 返回成功标志而不是response对象
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()
        return None, conversation_history


def run_interactive_mode(mcp_client):
    """交互模式 - 支持多轮对话"""
    print("\n" + "="*50)
    print("🎌 进入多轮对话模式 - 输入 'quit' 退出，'clear' 清空对话历史")
    print("="*50)
    
    # 维护对话历史
    conversation_history = []
    user_query_count = 0  # 单独跟踪用户真实查询次数
    
    while True:
        try:
            # 使用prompt_toolkit的prompt函数，提供更好的输入体验
            query = prompt("\n💬 请输入您的问题: ").strip()
            
            if query.lower() in ['quit', 'exit', '退出', 'q']:
                print("👋 再见！")
                break
            
            if query.lower() in ['clear', '清空', 'reset']:
                conversation_history = []
                user_query_count = 0  # 重置计数器
                print("🧹 对话历史已清空")
                continue
            
            if not query:
                continue
            
            # 增加用户查询计数
            user_query_count += 1
            
            # 显示对话轮次 - 使用单独的计数器
            print(f"\n🔄 第 {user_query_count} 轮对话 (历史消息: {len(conversation_history)} 条)")
            
            # 进行查询并更新对话历史
            success, conversation_history = query_with_mcp_tools(query, mcp_client, conversation_history)
            
            if success is None:
                print("⚠️ 本轮对话失败，但对话历史已保留")
            
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            print(f"❌ 处理输入时出错: {e}")

def run_test_queries(mcp_client):
    """运行预设的测试查询"""
    test_queries = [
        "请帮我查询这周的动漫播放安排，我想看看星期五有什么好看的番剧。",
        "今天有什么动漫播出？",
        "帮我查看星期一的番剧安排",
        "这周有哪些新番值得追？",
        "给我详细的本周动漫时间表"
    ]
    
    print("\n" + "="*50)
    print("🧪 开始运行测试查询")
    print("="*50)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*30}")
        print(f"🧪 测试查询 {i}/{len(test_queries)}")
        print(f"{'='*30}")
        
        query_with_mcp_tools(query, mcp_client)
        
        if i < len(test_queries):
            print("\n⏳ 等待 3 秒后继续下一个测试...")
            time.sleep(3)

def main():
    """主函数"""
    print("🚀 启动 MCP + Anthropic API 集成客户端")
    print("="*50)
    
    # 检查 API Key
    if not api_key:
        print("❌ 未找到 ANTHROPIC_API_KEY，请设置环境变量")
        return
    
    # 初始化 MCP 客户端
    mcp_client = MCPStdioClient(
        server_script_path="mcp_server.py",
        cwd="/Users/vsentkb/PycharmProjects/MCP"
    )
    
    try:
        # 启动服务器
        if not mcp_client.start_server():
            return
        
        # 等待服务器启动
        print("⏳ 等待服务器启动...")
        time.sleep(2)
        
        # 初始化连接
        if not mcp_client.initialize():
            print("❌ 初始化失败，输出调试信息:")
            mcp_client.debug_info()
            return
        
        # 等待初始化完成
        time.sleep(1)
        
        # 获取工具列表
        tools = mcp_client.list_tools()
        
        if not tools:
            print("❌ 未获取到工具，请检查您的 mcp_server.py 实现")
            mcp_client.debug_info()
            return
        
        print(f"\n🎉 MCP 客户端设置完成！获取到 {len(tools)} 个工具")
        
        # 选择运行模式
        print("\n请选择运行模式:")
        print("1. 运行预设测试查询")
        print("2. 进入交互模式")
        print("3. 同时运行测试和交互模式")
        
        choice = input("请输入选择 (1/2/3): ").strip()
        
        if choice == "1":
            run_test_queries(mcp_client)
        elif choice == "2":
            run_interactive_mode(mcp_client)
        elif choice == "3":
            run_test_queries(mcp_client)
            run_interactive_mode(mcp_client)
        else:
            print("❌ 无效选择，默认运行测试查询")
            run_test_queries(mcp_client)
        
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断")
    except Exception as e:
        print(f"❌ 运行时错误: {e}")
        import traceback
        traceback.print_exc()
        mcp_client.debug_info()
    finally:
        mcp_client.stop_server()
        print("\n🏁 程序结束")

if __name__ == "__main__":
    main()
