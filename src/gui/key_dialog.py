
import customtkinter as ctk

class ApiKeyWindow(ctk.CTk):

  def __init__(self):
    super().__init__()
    self.title("Enter gemini API key")
    self.geometry("350x180")
    self.resizable(False, False)
    self.api_key = None

    self.label = ctk.CTkLabel(
        self, text="An API key is required for the program to work:"
    )
    self.label.pack(pady=(20, 10))

    self.entry = ctk.CTkEntry(
        self, width=280, placeholder_text="Insert the key here...", show="*"
    )
    self.entry.pack(pady=5)

    self.btn = ctk.CTkButton(self, text="Save and continue", command=self.save)
    self.btn.pack(pady=15)

  def save(self):
    key = self.entry.get().strip()
    if key:
    #   save_api_key(key)
      self.api_key = key
      self.destroy()