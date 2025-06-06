import os
import subprocess
from rich import print
from dotenv import load_dotenv

import anthropic

load_dotenv()

api_key = os.environ.get("ANTHROPIC_API_KEY")
print(f"API Key loaded: {api_key[:10]}..." if api_key else "No API Key found")

# 启动MCP服务器作为子进程（stdio模式）
server_process = subprocess.Popen(
    ["python", "mcp_server.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    cwd="/Users/vsentkb/PycharmProjects/MCP"
)

client = anthropic.Anthropic(api_key=api_key)

# 测试动漫日历查询
try:
    response = client.beta.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2000,
        messages=[{
            "role": "user", 
            "content": "请帮我查询这周的动漫播放安排，我想看看星期五有什么好看的番剧。"
        }],
        mcp_servers=[
            {
                "type": "stdio",
                "command": "python",
                "args": ["mcp_server.py"],
                "name": "anime-calendar-server",
                "env": dict(os.environ)
            }
        ],
        extra_headers={
            "anthropic-beta": "mcp-client-2025-04-04"
        }
    )

    print("\n=== Claude 响应 ===")
    print(response.content)
    
finally:
    # 确保子进程被正确关闭
    if server_process:
        server_process.terminate()
        server_process.wait()

# 可以添加更多测试查询
def test_anime_queries():
    """测试不同的动漫查询"""
    queries = [
        "今天有什么动漫播出？",
        "帮我查看星期一的番剧安排",
        "这周有哪些新番值得追？",
        "给我详细的本周动漫时间表"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n=== 测试查询 {i} ===")
        print(f"查询: {query}")
        
        try:
            response = client.beta.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                messages=[{"role": "user", "content": query}],
                mcp_servers=[{
                    "type": "stdio",
                    "command": "python",
                    "args": ["mcp_server.py"],
                    "name": "anime-calendar-server",
                    "env": dict(os.environ)
                }],
                extra_headers={
                    "anthropic-beta": "mcp-client-2025-04-04"
                }
            )
            print("响应:")
            print(response.content)
        except Exception as e:
            print(f"查询失败: {e}")

# 取消注释来运行测试
# test_anime_queries()