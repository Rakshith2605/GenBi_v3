from langchain.memory import ConversationBufferMemory

user_memory_store = {}

def get_user_memory(user_id: str) -> ConversationBufferMemory:
    if user_id not in user_memory_store:
        user_memory_store[user_id] = ConversationBufferMemory()
    return user_memory_store[user_id]
