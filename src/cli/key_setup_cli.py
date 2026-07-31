from config.config_manager import ConfigManager


def setup_key_console(config: ConfigManager) -> str:
    print("--- First run: configuration settings ---")
    while True:
        user_input = input("Enter your Gemini API key: ").strip()
        if not user_input:
            print("The key cannot be empty. Please try again.")
            continue
        print("Verifying key via Gemini API...")
        if config.save_and_activate(user_input):
            print("Setup completed successfully!\n")
            return user_input
        print("Invalid key or internet problem. Try again.")
