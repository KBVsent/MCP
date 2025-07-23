from fastmcp import FastMCP
import boto3
from botocore.exceptions import ClientError
from typing import Annotated
from pydantic import Field
import time

mcp = FastMCP("AWS EC2 Controller")

# 初始化EC2客户端
ec2 = boto3.client('ec2', region_name='ap-northeast-1')
instance_id = 'i-07e3eba501133ef6a'

@mcp.tool()
def start_ec2_instance(
    max_retries: Annotated[
        int,
        Field(
            description="最大重试次数，默认为3次",
            ge=1,
            le=10
        )
    ] = 3,
    wait_seconds: Annotated[
        int,
        Field(
            description="重试间隔时间（秒），默认为1秒",
            ge=1,
            le=60
        )
    ] = 1
) -> dict:
    """启动AWS EC2实例
    
    启动指定的EC2实例，支持重试机制处理容量不足的情况。
    会自动处理实例容量不足的错误并进行重试。
    
    返回启动结果和当前实例状态信息。
    """
    retries = 0
    while retries < max_retries:
        try:
            response = ec2.start_instances(InstanceIds=[instance_id])
            current_state = response['StartingInstances'][0]['CurrentState']['Name']
            return {
                "success": True,
                "message": f"实例 {instance_id} 启动请求已发送",
                "current_state": current_state,
                "instance_id": instance_id,
                "retries_used": retries
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'InsufficientInstanceCapacity':
                retries += 1
                if retries < max_retries:
                    time.sleep(wait_seconds)
                    continue
                else:
                    return {
                        "success": False,
                        "error": "容量不足",
                        "message": f"实例 {instance_id} 启动失败，达到最大重试次数",
                        "retries_used": retries,
                        "instance_id": instance_id
                    }
            else:
                return {
                    "success": False,
                    "error": error_code,
                    "message": f"实例 {instance_id} 启动失败: {str(e)}",
                    "instance_id": instance_id
                }
        except Exception as e:
            return {
                "success": False,
                "error": "未知错误",
                "message": f"实例 {instance_id} 启动时发生未知错误: {str(e)}",
                "instance_id": instance_id
            }
    
    return {
        "success": False,
        "error": "重试次数耗尽",
        "message": f"实例 {instance_id} 启动失败，达到最大重试次数",
        "retries_used": retries,
        "instance_id": instance_id
    }

@mcp.tool()
def stop_ec2_instance() -> dict:
    """停止AWS EC2实例
    
    停止指定的EC2实例。
    
    返回停止结果和当前实例状态信息。
    """
    try:
        response = ec2.stop_instances(InstanceIds=[instance_id])
        current_state = response['StoppingInstances'][0]['CurrentState']['Name']
        return {
            "success": True,
            "message": f"实例 {instance_id} 停止请求已发送",
            "current_state": current_state,
            "instance_id": instance_id
        }
    except ClientError as e:
        return {
            "success": False,
            "error": e.response['Error']['Code'],
            "message": f"实例 {instance_id} 停止失败: {str(e)}",
            "instance_id": instance_id
        }
    except Exception as e:
        return {
            "success": False,
            "error": "未知错误",
            "message": f"实例 {instance_id} 停止时发生未知错误: {str(e)}",
            "instance_id": instance_id
        }

@mcp.tool()
def get_ec2_instance_status() -> dict:
    """获取AWS EC2实例当前状态
    
    查询指定EC2实例的当前运行状态。
    
    返回实例的详细状态信息。
    """
    try:
        response = ec2.describe_instances(InstanceIds=[instance_id])
        state = response['Reservations'][0]['Instances'][0]['State']['Name']
        return {
            "success": True,
            "instance_id": instance_id,
            "current_state": state,
            "message": f"实例 {instance_id} 当前状态: {state}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": "查询失败",
            "message": f"检查实例状态失败: {str(e)}",
            "instance_id": instance_id
        }

if __name__ == "__main__":
    mcp.run()