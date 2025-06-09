import os
import anthropic
from rich import print
from rich.console import Console
import sys

# Your server URL (replace with your actual URL)
url = 'https://b.moev.cc/ccp'

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
    # 显示连接状态
    print("[yellow]⏳ 连接中...[/yellow]")
    
    response = client.beta.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": "告诉我这周一的番剧，给出简略的信息。"}],
        mcp_servers=[
            {
                "type": "url",
                "url": f"{url}/mcp",
                "name": "AnimeAndWeatherAssistant",
            }
        ],
        extra_headers={
            "anthropic-beta": "mcp-client-2025-04-04"
        },
        stream=True  # 启用流式响应
    )
    
    print("[green]✓ 已连接，开始接收回复...[/green]\n")
    print("[bold cyan]📥 Claude 回复：[/bold cyan]")
    print("─" * 50)
    
    # 实时显示流式响应
    full_response = ""
    content_started = False
    
    for chunk in response:
        if chunk.type == "message_start":
            continue  # 静默处理
        elif chunk.type == "content_block_start":
            if not content_started:
                content_started = True
                # 开始内容输出，不显示调试信息
        elif chunk.type == "content_block_delta":
            if hasattr(chunk.delta, 'text'):
                text_chunk = chunk.delta.text
                # 直接输出文本，不添加任何额外信息
                sys.stdout.write(text_chunk)
                sys.stdout.flush()
                full_response += text_chunk
        elif chunk.type == "content_block_stop":
            continue  # 静默处理
        elif chunk.type == "message_stop":
            break  # 结束处理
    
    # 输出完成后的信息
    print("\n\n" + "─" * 50)
    print(f"[bold green]✅ 响应完成！总字符数: {len(full_response)}[/bold green]")
    
except Exception as e:
    print(f"\n[bold red]❌ 请求失败: {str(e)}[/bold red]")
    print("[dim]请检查网络连接和API密钥[/dim]")