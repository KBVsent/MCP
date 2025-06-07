import os
import anthropic
from rich import print
from rich.console import Console
from rich.spinner import Spinner
from rich.live import Live
import time

# Your server URL (replace with your actual URL)
url = 'https://b.moev.cc/mcp'

api_key = os.environ.get("ANTHROPIC_API_KEY")
print(f"API Key loaded: {api_key[:10]}..." if api_key else "No API Key found")

client = anthropic.Anthropic(api_key=api_key)
console = Console()

# 显示开始请求的状态
print("\n[bold blue]🚀 正在发送请求到 MCP 服务器...[/bold blue]")
print(f"[dim]服务器地址: {url}[/dim]")
print(f"[dim]模型: claude-sonnet-4-20250514[/dim]")
print("[dim]查询内容: 告诉我这周日的番剧[/dim]\n")

try:
    # 使用流式响应
    with console.status("[bold green]等待 Claude 响应中...", spinner="dots") as status:
        response = client.beta.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": "告诉我这周日的番剧"}],
            mcp_servers=[
                {
                    "type": "url",
                    "url": f"{url}/sse",
                    "name": "AnimeAndWeatherAssistant",
                }
            ],
            extra_headers={
                "anthropic-beta": "mcp-client-2025-04-04"
            },
            stream=True  # 启用流式响应
        )
        
        status.update("[bold green]正在接收响应...")
        
        print("\n[bold cyan]📥 Claude 回复：[/bold cyan]")
        print("─" * 50)
        
        # 实时显示流式响应
        full_response = ""
        for chunk in response:
            if chunk.type == "message_start":
                print("[dim]开始接收消息...[/dim]")
            elif chunk.type == "content_block_start":
                print("[dim]内容块开始...[/dim]")
            elif chunk.type == "content_block_delta":
                if hasattr(chunk.delta, 'text'):
                    text_chunk = chunk.delta.text
                    print(text_chunk, end='', flush=True)
                    full_response += text_chunk
            elif chunk.type == "content_block_stop":
                print("\n[dim]内容块结束[/dim]")
            elif chunk.type == "message_stop":
                print("\n[dim]消息接收完成[/dim]")
        
        print("\n" + "─" * 50)
        print(f"[bold green]✅ 响应完成！总字符数: {len(full_response)}[/bold green]")
        
except Exception as e:
    print(f"\n[bold red]❌ 请求失败: {str(e)}[/bold red]")
    print("[dim]请检查网络连接和API密钥[/dim]")