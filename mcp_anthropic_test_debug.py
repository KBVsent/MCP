import os
import anthropic
from rich import print
from rich.console import Console
from rich.pretty import pprint
import sys
import json
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# Your server URL (replace with your actual URL)
url = os.environ.get("MCP_SERVER_URL")

api_key = os.environ.get("ANTHROPIC_API_KEY")
print(f"API Key loaded: {api_key[:10]}..." if api_key else "No API Key found")

client = anthropic.Anthropic(api_key=api_key)
console = Console()

# 显示开始请求的状态
print("\n[bold blue]🚀 正在发送请求到 MCP 服务器...[/bold blue]")
print(f"[dim]服务器地址: {url}[/dim]")
print(f"[dim]模型: claude-sonnet-4-20250514[/dim]")

try:
    # 显示连接状态
    print("[yellow]⏳ 连接中...[/yellow]")
    
    response = client.beta.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": "在线查询今日新闻"}],
        mcp_servers=[
            {
                "type": "url",
                "url": f"{url}",
                "name": "Perplexity Search MCP Server",
            }
        ],
        extra_headers={
            "anthropic-beta": "mcp-client-2025-04-04"
        },
        stream=False  # 关闭流式响应，获取完整响应
    )
    
    print("[green]✓ 已连接，接收到完整回复[/green]\n")
    print("[bold cyan]📥 Claude 完整响应详情：[/bold cyan]")
    print("─" * 60)
    print("[dim]💡 显示完整的响应对象以便调试[/dim]\n")
    
    # 显示完整的响应信息
    print("[bold blue]🔍 完整响应对象：[/bold blue]")
    pprint(response)
    
    print("\n" + "─" * 60)
    print("[bold green]� 响应内容：[/bold green]")
    
    # 提取并显示文本内容
    if hasattr(response, 'content') and response.content:
        for i, content_block in enumerate(response.content):
            print(f"[yellow]📝 内容块 {i+1}:[/yellow]")
            if hasattr(content_block, 'type'):
                print(f"[dim]   类型: {content_block.type}[/dim]")
            if hasattr(content_block, 'text'):
                print(f"[cyan]   文本: {content_block.text}[/cyan]")
            else:
                print(f"[magenta]   内容: {content_block}[/magenta]")
            print()
    
    # 显示其他有用的响应信息
    print("─" * 60)
    print("[bold blue]📊 响应元数据：[/bold blue]")
    if hasattr(response, 'usage'):
        print(f"[dim]Token使用情况: {response.usage}[/dim]")
    if hasattr(response, 'model'):
        print(f"[dim]使用的模型: {response.model}[/dim]")
    if hasattr(response, 'id'):
        print(f"[dim]响应ID: {response.id}[/dim]")
    
    print(f"[bold green]✅ 调试信息显示完成！[/bold green]")
    
except Exception as e:
    print(f"\n[bold red]❌ 请求失败: {str(e)}[/bold red]")
    print("[dim]请检查网络连接和API密钥[/dim]")