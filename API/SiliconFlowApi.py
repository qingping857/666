from typing import Optional, Dict, Any, Union
from dataclasses import dataclass
import logging
from enum import Enum
from config import Config
from API.StreamResponse import StreamConfig, StreamResponseHandler


class ModelType(Enum):
    """SiliconFlow 模型类型枚举"""
    V3 = "V3"  # DeepSeek V3 模型
    R1 = "R1"  # DeepSeek R1 模型

    def __str__(self):
        return self.value

    @classmethod
    def from_string(cls, value: str) -> 'ModelType':
        """
        从字符串创建 ModelType

        Args:
            value: 模型类型字符串

        Returns:
            ModelType: 对应的枚举值

        Raises:
            ValueError: 当字符串不匹配任何模型类型时
        """
        try:
            return cls(value.upper())
        except ValueError:
            raise ValueError(f"无效的模型类型: {value}. 有效值为: {', '.join(m.value for m in cls)}")


@dataclass
class SiliconFlowConfig:
    """SiliconFlow API 配置类"""
    api_key: str = Config.SILICONFLOW_API_KEY
    base_url: str = "https://api.siliconflow.cn/v1"
    temperature: float = 0.7
    max_tokens: int = 4069
    frequency_penalty: float = 1.0
    top_k: int = 50
    top_p: float = 1.0
    model_prefix: str = "deepseek-ai/DeepSeek-"
    default_model: ModelType = ModelType.R1


class SiliconFlowClient:
    def __init__(self, config: Optional[SiliconFlowConfig] = None):
        """
        初始化 SiliconFlow 客户端

        Args:
            config: API 配置，如果不提供则使用默认值
        """
        self.config = config or SiliconFlowConfig()
        self.stream_handler = StreamResponseHandler()
        self._setup_logging()

    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('SiliconFlow')

    def _validate_parameters(self, model_type: ModelType, question: str) -> None:
        """
        验证输入参数

        Args:
            model_type: 模型类型
            question: 问题内容

        Raises:
            ValueError: 当参数无效时抛出
        """
        if not isinstance(model_type, ModelType):
            raise ValueError(f"model_type 必须是 ModelType 枚举值, 而不是 {type(model_type)}")

        if not question or not isinstance(question, str):
            raise ValueError("question 必须是非空字符串")

        if self.config.temperature < 0 or self.config.temperature > 1:
            raise ValueError("temperature 必须在 0 和 1 之间")

    def _prepare_payload(self, model_type: ModelType, question: str) -> Dict[str, Any]:
        """
        准备 API 请求的 payload

        Args:
            model_type: 模型类型
            question: 问题内容

        Returns:
            Dict: API 请求的 payload
        """
        return {
            "model": f"{self.config.model_prefix}{str(model_type)}",
            "temperature": self.config.temperature,
            "stream": True,
            "messages": [
                {
                    "content": question,
                    "role": "user"
                }
            ],
            "frequency_penalty": self.config.frequency_penalty,
            "max_tokens": self.config.max_tokens,
            "n": 1,
            "response_format": {"type": "text"},
            "top_k": self.config.top_k,
            "top_p": self.config.top_p
        }

    def _get_headers(self) -> Dict[str, str]:
        """
        获取 API 请求头

        Returns:
            Dict: API 请求头
        """
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

    def chat(self,
             model_type: Union[ModelType, str, None] = None,
             question: str = "") -> Union[str, Dict[str, Any]]:
        """
        发送聊天请求

        Args:
            model_type: 模型类型，可以是 ModelType 枚举值或字符串
            question: 问题内容

        Returns:
            Union[str, Dict]: API 响应或错误信息
        """
        try:
            # 处理模型类型
            if model_type is None:
                model_type = self.config.default_model
            elif isinstance(model_type, str):
                model_type = ModelType.from_string(model_type)

            # 验证参数
            self._validate_parameters(model_type, question)

            # 准备请求
            url = f"{self.config.base_url}/chat/completions"
            payload = self._prepare_payload(model_type, question)
            headers = self._get_headers()

            # 记录请求
            self.logger.info(f"Sending request to {url} with model {model_type}")
            self.logger.debug(f"Payload: {payload}")

            # 发送请求并获取响应
            response = self.stream_handler.stream_response(url, payload, headers)

            # 记录响应
            self.logger.info("Request completed successfully")

            return response

        except ValueError as e:
            error_msg = f"参数错误: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"请求处理错误: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}


# 使用示例
def siliconflow(
        model_type: Union[ModelType, str, None] = None,
        question: str = ""
) -> Union[str, Dict[str, Any]]:
    """
    SiliconFlow API 的便捷调用函数

    Args:
        model_type: 模型类型，可以是 ModelType 枚举值或字符串
        question: 问题内容

    Returns:
        Union[str, Dict]: API 响应或错误信息
    """
    try:
        client = SiliconFlowClient()
        return client.chat(model_type, question)
    except Exception as e:
        return {"error": f"API 调用失败: {str(e)}"}


if __name__ == "__main__":
    # siliconflow使用示例
    title = "Computer Service"
    question1 = '''请判断以下项目 title 是否与计算机相关，仅返回 'yes' 或 'no'。
    示例：
    1. "AI-Powered Data Analytics Platform" → yes
    2. "Cloud Computing Infrastructure Upgrade" → yes
    3. "Cybersecurity Risk Assessment" → yes
    4. "Bridge Construction and Design" → no
    5. "Urban Traffic Flow Optimization" → no

    项目 title: '''
    response = siliconflow(ModelType.V3, question1 + title)