import json
import os
from typing import Dict, Any

class Database:
    def __init__(self):
        self.user_data_file = "user_data.json"
        self.group_data_file = "group_data.json"
        self.load_data()

    def load_data(self) -> None:
        """Load data from JSON files."""
        self.user_data = self._load_json(self.user_data_file, {})
        self.group_data = self._load_json(self.group_data_file, {})

    def save_data(self) -> None:
        """Save data to JSON files."""
        self._save_json(self.user_data_file, self.user_data)
        self._save_json(self.group_data_file, self.group_data)

    def _load_json(self, filename: str, default: Any) -> Any:
        """Load data from JSON file."""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return default

    def _save_json(self, filename: str, data: Any) -> None:
        """Save data to JSON file."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving {filename}: {e}")

    def get_user(self, user_id: int) -> Dict:
        """Get user data."""
        return self.user_data.get(str(user_id), {})

    def save_user(self, user_id: int, data: Dict) -> None:
        """Save user data."""
        self.user_data[str(user_id)] = data
        self.save_data()

    def get_group(self, group_id: str) -> Dict:
        """Get group data."""
        return self.group_data.get(group_id, {})

    def save_group(self, group_id: str, data: Dict) -> None:
        """Save group data."""
        self.group_data[group_id] = data
        self.save_data()

    def delete_group(self, group_id: str) -> None:
        """Delete group data."""
        if group_id in self.group_data:
            del self.group_data[group_id]
            self.save_data()

    def update_user_stats(self, user_id: int, chat_count: int = 0, message_count: int = 0) -> None:
        """Update user statistics."""
        user_data = self.get_user(user_id)
        if "stats" not in user_data:
            user_data["stats"] = {"total_chats": 0, "messages_sent": 0}
        
        user_data["stats"]["total_chats"] += chat_count
        user_data["stats"]["messages_sent"] += message_count
        self.save_user(user_id, user_data)

# Create global database instance
db = Database() 