import json
import streamingjson
from db_agent.utils.output_stream import OutputStream

from openai.types.chat import ChatCompletionChunk

from db_agent.utils.stream_printer import StreamPrinter

class ChunkPrinter(StreamPrinter):
    def __init__(self, output_stream: OutputStream):
        super().__init__()
        self._output_stream = output_stream
        self._lexers:list[streamingjson.Lexer] = []
        self._tool_call_para:list[str] = []
        self._function_names:list[str] = []
        self.started:bool = False

    async def print_sequential_thinking_parameters(self, lexer: streamingjson.Lexer, seg: str, call_id: int):
        lexer.append_string(seg)
        try:
            json_complete = lexer.complete_json()
            func = json.loads(json_complete)
        except json.JSONDecodeError:
            return
        except Exception as e:
            return

        if func.get("thought") is None:
            return
        
        if len(func["thought"]) > len(self._tool_call_para[call_id]):
            msg = func["thought"][len(self._tool_call_para[call_id]):]
            self._tool_call_para[call_id] = func["thought"]
            if not self.started:
                self.started = True
                await self._output_stream.start_chunk()
            await self._output_stream.send_chunk(msg)

    async def print_chunk(self, chunk: ChatCompletionChunk):
        if chunk.choices:
            choice = chunk.choices[0]
            delta = choice.delta
            
            # 收集文本内容
            if delta.content is not None and len(delta.content) > 0:
                if not self.started:
                    self.started = True
                    await self._output_stream.start_chunk()
                await self._output_stream.send_chunk(delta.content)

            # 收集工具调用
            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    lexer : streamingjson.Lexer = None                   
                    # 处理新工具调用
                    if tool_call.index >= len(self._lexers):
                        lexer = streamingjson.Lexer()
                        self._lexers.append(lexer)
                        self._tool_call_para.append("")
                        self._function_names.append(tool_call.function.name)
                    # 追加现有工具调用的参数
                    else:
                        lexer = self._lexers[tool_call.index]

                    if self._function_names[tool_call.index] == "sequentialthinking":
                        await self.print_sequential_thinking_parameters(
                            lexer, tool_call.function.arguments, tool_call.index
                        )
