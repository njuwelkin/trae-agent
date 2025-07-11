import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from agent.session_manager import SessionManager, Session
from agent.mcp_client_manager import MCPClientManager
from agent.agent import Agent
from utils.config import load_config, Config, ModelParameters
from utils.output_stream import WebSocketOutputStream
from utils.llm_client import LLMClient

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_chat_interface():
    return FileResponse("static/index.html")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    session_manager: SessionManager = app.state.session_manager
    await websocket.accept()

    session: Session = session_manager.new_session()
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            m_type = message.get("type", message)
            m_content = message.get("content", "")
            if m_type == "message":
                conversation = session.newConversation()
                conversation.context["user_message"] = m_content
                conversation.context["output_stream"] = WebSocketOutputStream(websocket)
                conversation.context["mcp_client"] = app.state.mcp_client_manager.get_client("")
                # todo: get db info from message and create the right mcp client
                config: Config = app.state.config
                conversation.context["llm_client"] = LLMClient(
                    config.default_provider, config.model_providers[config.default_provider]
                )
                agent = Agent()
                await agent.run(conversation)
            elif m_type == "acknowledge":
                if m_content == "cancel" or m_content == "":
                    continue
                else:
                    conversation = session.conversations.get(conversation.id)
                    if conversation is None:
                        websocket.send_text(json.dumps({"type": "error", "content": "conversation not found"}))
                        continue
                    conversation.context['is_continue'] = True
                    agent = Agent()
                    await agent.run(conversation)
            
    except WebSocketDisconnect:
        session_manager.delete_session(session.id)


@app.on_event("startup")
async def startup_event():
    app.state.config = load_config()
    app.state.session_manager = SessionManager()
    # TODO：config中加上mcp相关配置，以及最大重试次数
    app.state.mcp_client_manager = MCPClientManager()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 