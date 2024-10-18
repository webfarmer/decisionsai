from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from PyQt6.QtCore import QObject, pyqtSignal
from typing import List
import numpy as np
import json
import os
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound
from distr.core.db import get_session, Chat
from distr.core.constants import CORRECTIONS
from difflib import SequenceMatcher
from langchain_community.llms import Ollama
from ollama import Client


class ChatManager(QObject):
    chat_updated = pyqtSignal(int)  # Signal to emit when a chat is updated
    chat_created = pyqtSignal(int)  # New signal
    chat_deleted = pyqtSignal(int)  # New signal
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        super().__init__()
        try:
            print(f"Loading SBERT model: {model_name}")
            self.sbert_model = SentenceTransformer(model_name)
            print("SBERT model loaded successfully")
        except Exception as e:
            print(f"Error loading SBERT model: {e}")
            print("Falling back to default model: 'sentence-transformers/all-MiniLM-L6-v2'")
            self.sbert_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

        # Initialize Ollama
        self.client = Client()
        
        # Set up the agent's profile prompt
        self.agent_prompt = """
        You are an AI assistant named Jax. 
        You part of an application called DecisionsAI created by
        a company called Crystal Logic.
        You are designed to be a helpful, harmless, and honest assistant.
        You are predomintely an assistant who is offline, but can run system
        commands and control the user's computer's user. The user just needs
        to provide you with a command and you will complete it for them.
        You have a wide range of knowledge and can assist with various tasks, 
        but you also know your limitations. 
        When you're not sure about something, you say so. 
        You're friendly and conversational, but you maintain appropriate boundaries. 
        You don't pretend to have human experiences or emotions. 
        Your responses are concise and to the point, avoiding unnecessary verbosity.
        You aim to provide accurate and helpful information 
        to the best of your abilities.
        """    
        
        # Initialize conversation history with the agent prompt
        self.conversation_history = [
            {"role": "system", "content": self.agent_prompt}
        ]

        # Load trigger words
        with open(os.path.join(os.path.dirname(__file__), 'actions.config.json'), 'r') as f:
            config = json.load(f)
        self.trigger_words = [action["trigger"] for action in config["actions"] if "trigger" in action]

    def get_closest_trigger(self, input_text: str, threshold: float = 0.7) -> tuple:
        input_embedding = self.sbert_model.encode([input_text])[0]
        trigger_embeddings = self.sbert_model.encode(self.trigger_words)
        
        similarities = cosine_similarity([input_embedding], trigger_embeddings)[0]
        best_match_index = np.argmax(similarities)
        best_match_similarity = similarities[best_match_index]
        
        if best_match_similarity >= threshold:
            return self.trigger_words[best_match_index], best_match_similarity
        else:
            return None, 0.0

    def refine_prompt(self, action: dict, trigger_sentences: List[str], transcription: str, end_words: List[str]) -> str:
        print("PROMPT TEMPLATE...")
        print(f"Trigger sentences: {trigger_sentences}")
        print(f"Transcription: {transcription}")
        print(f"End words: {end_words}")

        refined_content = []
        transcription_lower = transcription.lower()

        # Always include the first trigger sentence if it's a common starting phrase
        
        common_starts = [action["trigger"]] + action.get("trigger_variants", [])
        if any(trigger_sentences[0].lower().startswith(start.lower()) for start in common_starts):
            refined_content.append(trigger_sentences[0])

        for trigger in trigger_sentences:
            trigger_lower = trigger.lower()
            if trigger_lower in transcription_lower:
                refined_content.append(trigger)
            else:
                # Check for partial matches
                trigger_words = trigger_lower.split()
                transcription_words = transcription_lower.split()
                matched_words = [word for word in trigger_words if any(SequenceMatcher(None, word, trans_word).ratio() > 0.8 for trans_word in transcription_words)]
                if len(matched_words) / len(trigger_words) > 0.5:  # If more than half the words match
                    refined_content.append(trigger)

        if not refined_content:
            refined_content = [transcription]

        refined_content = " ".join(refined_content)

        # Remove the end phrase if present
        for end_word in end_words:
            end_index = refined_content.lower().rfind(end_word.lower())
            if end_index != -1:
                refined_content = refined_content[:end_index].strip()
                break

        print(f"Refined content: {refined_content}")
        
        return refined_content if refined_content else "<unrecognised>"

    def apply_corrections(self, phrase):
        words = phrase.split()
        corrected_words = [CORRECTIONS.get(word.lower(), word) for word in words]
        return " ".join(corrected_words)

    def find_best_match(self, target, options, threshold=0.6):
        best_match = None
        best_ratio = 0
        for option in options:
            ratio = SequenceMatcher(None, target.lower(), option.lower()).ratio()
            if ratio > best_ratio and ratio > threshold:
                best_ratio = ratio
                best_match = option
        return best_match

    def find_best_matches(self, target, options):
        matches = []
        for option in options:
            ratio = SequenceMatcher(None, target.lower(), option.lower()).ratio()
            if ratio > 0.6:
                matches.append((option, ratio))
        return sorted(matches, key=lambda x: x[1], reverse=True)

    def process_voice_input(self, action:dict, input_text: str) -> str:
        refined_content = self.refine_prompt(action, [input_text], input_text, [])
        if refined_content != "<unrecognised>":
            self.chat_updated.emit(0)  # Emit signal with a dummy chat ID
            return f"Processed: {refined_content}"
        else:
            return "I'm sorry, I couldn't understand that. Could you please rephrase?"

    def is_recognised(self, action:dict, input_text: str) -> bool:
        return self.refine_prompt(action, [input_text], input_text, []) != "<unrecognised>"

    def create_chat(self, title, input_text=""):
        session = get_session()
        new_chat = Chat(
            title=title,
            input=input_text,
            response="",
            params=json.dumps({}),
            created_date=datetime.utcnow(),
            modified_date=datetime.utcnow()
        )
        session.add(new_chat)
        session.commit()
        new_chat_id = new_chat.id
        session.close()
        self.chat_created.emit(new_chat_id)
        return new_chat_id

    def delete_chat(self, chat_id):
        session = get_session()
        try:
            chat = session.query(Chat).filter(Chat.id == chat_id).one()
            session.delete(chat)
            session.commit()
            self.chat_deleted.emit(chat_id)
        except NoResultFound:
            print(f"Chat with id {chat_id} not found.")
        finally:
            session.close()

    # Add this new method
    def process_prompt(self, prompt):
        # Add user input to conversation history
        self.conversation_history.append({"role": "user", "content": prompt})

        # Create the messages list with conversation history
        messages = self.conversation_history.copy()

        # Generate response using the Ollama model
        response = self.client.chat(model="gemma2:latest",messages=messages)

        ai_response = response['message']['content']

        # Add AI response to conversation history
        self.conversation_history.append({"role": "assistant", "content": ai_response})

        # Limit conversation history to last 10 exchanges (20 messages)
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

        return response

    def set_tts_manager(self, tts_manager):
        self.tts_manager = tts_manager

    def start_tts(self, text):
        self.tts_manager.start_tts(text)

def initialize_chat_manager():
    chat_manager = ChatManager()
    print("Chat Manager initialized successfully.")
    return chat_manager