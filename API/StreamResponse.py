import re
from typing import Optional, Dict, Any
from dataclasses import dataclass
import json
import requests
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class StreamConfig:
    """流式响应的配置类"""
    # 文本清理配置
    remove_markdown: bool = True
    remove_html_tags: bool = True
    remove_html_entities: bool = True
    remove_special_chars: bool = True
    remove_special_markers: bool = True
    normalize_whitespace: bool = True
    preserve_paragraphs: bool = True

    # 流式处理配置
    stream_print: bool = True
    max_retries: int = 3  # 最大重试次数
    retry_delay: float = 2.0  # 重试延迟（秒）
    timeout: float = 60.0  # 请求超时（秒）


class StreamResponseHandler:
    def __init__(self, config: Optional[StreamConfig] = None):
        self.config = config or StreamConfig()
        self._init_patterns()
        self.retry_codes = {408, 429, 500, 502, 503, 504}  # 需要重试的状态码

    def _init_patterns(self):
        """初始化清理文本用的正则表达式模式"""
        # 更高效的模式实现
        self.patterns = {
            'headers': re.compile(r'-*#{1,3}\s*\*{0,2}'),
            'bold_italic': re.compile(r'\*{1,4}([^*]+?)\*{1,4}'),
            'numbering': re.compile(r'(\d+)\.\s*\*{0,2}'),
            'chinese_numbering': re.compile(r'([一二三四五六七八九十]+、)\s*\*{0,2}'),
            'special_combos': re.compile(r'(-\s*\*{2}|\*{2}-)'),
            'list_markers': re.compile(r'^\s*-\s+'),
            'special_chars': re.compile(r'[▪▶︎✓➤▫•※☆★○●◎◇◆□■△▲▽▼→←↑↓↔↕]'),
            'brackets': re.compile(r'【(.*?)】')
        }

        # HTML 实体映射
        self.html_entities = {
            'andnbsp;': ' ',
            '&nbsp;': ' ',
            '&lt;': '<',
            '&gt;': '>',
            '&amp;': '&',
            '&quot;': '"',
            '&apos;': "'",
        }

        # 要移除的字符列表
        self.chars_to_remove = '*-\\|【】▌—'

    def _clean_text(self, content: str) -> str:
        """清理文本内容"""
        if not content:
            return ""

        # 1. 预处理：统一换行符
        content = content.replace('\r\n', '\n').replace('\r', '\n')

        # 2. 使用我们更高效的模式进行处理
        for pattern_key, pattern in self.patterns.items():
            if pattern_key == 'bold_italic':
                content = pattern.sub(r'\1', content)
            else:
                content = pattern.sub('', content)

        # 3. 处理 HTML 实体
        if self.config.remove_html_entities:
            # 按长度排序确保长的实体先被替换
            sorted_entities = sorted(
                self.html_entities.items(),
                key=lambda x: len(x[0]),
                reverse=True
            )
            for entity, replacement in sorted_entities:
                content = content.replace(entity, replacement)

        # 4. 移除特定字符
        for char in self.chars_to_remove:
            content = content.replace(char, "")

        # 5. 最终清理
        content = content.strip()

        # 6. 处理段落（如果配置要求）
        if getattr(self.config, 'preserve_paragraphs', False):
            # 确保章节之间有空行
            content = re.sub(r'(?<=\.)\s*([一二三四五六七八九十]、)', r'\n\n\1', content)
            # 确保段落之间只有一个空行
            content = re.sub(r'\n{3,}', '\n\n', content)

        return content

    def _extract_content(self, json_response: Dict[str, Any]) -> Optional[str]:
        """从JSON响应中提取内容"""
        # 检查错误
        if 'error' in json_response:
            error_msg = json_response.get('error', {}).get('message', '未知错误')
            raise ValueError(f"API返回错误: {error_msg}")

        # 尝试获取内容 - 支持多种响应格式
        if 'choices' in json_response and json_response['choices']:
            delta = json_response['choices'][0].get('delta', {})
            content = delta.get('content')
        else:
            content = json_response.get('response')

        return content

    def _process_line(self, line: bytes) -> Optional[str]:
        """处理单行响应"""
        try:
            line_text = line.decode('utf-8')

            # 处理前缀和心跳
            if line_text.startswith('data: '):
                line_text = line_text[6:]
            if line_text.strip() == '[DONE]':
                return None

            # 解析JSON
            json_response = json.loads(line_text)
            content = self._extract_content(json_response)

            if content:
                return self._clean_text(content)

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
            raise ValueError(f"JSON解析错误: {e}")
        except Exception as e:
            logger.error(f"处理响应时出错: {e}")
            raise Exception(f"处理响应时出错: {e}")

        return None

    def stream_response(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> str:
        """处理流式响应的主函数"""
        buffer = ""
        attempt = 0

        while True:
            try:
                session = requests.Session()
                response = session.post(
                    url,
                    json=payload,
                    headers=headers,
                    stream=True,
                    timeout=(5, self.config.timeout)  # (连接超时, 读取超时)
                )

                # 检查响应状态
                if response.status_code != 200:
                    if response.status_code in self.retry_codes and attempt < self.config.max_retries:
                        retry_delay = self.config.retry_delay * (2 ** attempt)
                        print(f"\n请求失败，{retry_delay:.1f}秒后重试 ({attempt + 1}/{self.config.max_retries})...")
                        time.sleep(retry_delay)
                        attempt += 1
                        continue
                    response.raise_for_status()

                # 处理响应内容
                for line in response.iter_lines():
                    if not line:
                        continue

                    try:
                        content = self._process_line(line)
                        if content:
                            if self.config.stream_print:
                                print(content, end='', flush=True)
                            buffer += content
                    except ValueError as e:
                        print(f"\n处理响应行时出错: {e}")
                        continue

                # 成功完成，跳出循环
                break

            except (requests.Timeout, requests.ConnectionError) as e:
                logger.error(f"请求错误: {str(e)}")
                status_code = 504 if isinstance(e, requests.Timeout) else 503
                if status_code in self.retry_codes and attempt < self.config.max_retries:
                    retry_delay = self.config.retry_delay * (2 ** attempt)
                    print(f"\n请求失败，{retry_delay:.1f}秒后重试 ({attempt + 1}/{self.config.max_retries})...")
                    time.sleep(retry_delay)
                    attempt += 1
                    continue
                error_msg = f"HTTP请求错误: {e}"
                print(f"\n{error_msg}")
                return error_msg

            except Exception as e:
                logger.error(f"未知错误: {str(e)}")
                error_msg = f"未知错误: {e}"
                print(f"\n{error_msg}")
                return error_msg

            finally:
                if 'session' in locals():
                    session.close()

        return buffer