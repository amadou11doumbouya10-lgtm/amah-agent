import importlib

# Source unique de TOOL_FUNCTIONS : chaque entrée associe un module à la liste
# des fonctions qu'il expose comme outils pour l'agent. Le dict est construit
# par introspection ci-dessous -- un nom n'est écrit qu'une seule fois (au lieu
# d'un import + une entrée de dict à maintenir en double).
_TOOL_MODULES = [
    ("tools.files", [
        "list_files", "organize_folder", "find_files", "move_file",
        "create_folder", "read_file", "write_file", "edit_file", "edit_pdf",
        "get_folder_info", "delete_file", "summarize",
    ]),
    ("tools.documents", ["create_word", "create_txt", "create_pdf", "read_document"]),
    ("tools.search", ["web_search", "read_webpage"]),
    ("tools.system", ["get_system_info", "open_file", "run_command", "kill_process"]),
    ("tools.memory", ["save_memory", "get_memories", "delete_memory"]),
    ("tools.email_tool", ["read_emails", "send_email", "search_emails", "draft_email"]),
    ("tools.browser", ["open_browser", "click_element", "fill_form", "take_screenshot", "get_page_text"]),
    ("tools.voice", ["speak"]),
    ("tools.notifications", ["send_notification", "set_reminder"]),
    ("tools.excel", ["read_excel", "create_excel", "append_to_excel"]),
    ("tools.clipboard", ["read_clipboard", "write_clipboard"]),
    ("tools.utils", ["calculate", "get_datetime", "add_days", "generate_password", "convert_units"]),
    ("tools.archive", ["zip_files", "unzip_file", "list_archive"]),
    ("tools.image_tool", [
        "screenshot_full", "resize_image", "get_image_info", "convert_image",
        "list_processes", "get_network_info",
    ]),
    ("tools.meteo", ["get_weather", "get_weather_simple"]),
    ("tools.translator", ["translate", "detect_language"]),
    ("tools.qrcode_tool", ["create_qrcode"]),
    ("tools.voice_recognition", ["listen", "listen_continuous"]),
    ("tools.scheduler", ["create_daily_task", "list_tasks", "delete_task", "run_task_now"]),
    ("tools.stats", ["get_stats", "reset_stats"]),
    ("tools.updater", ["check_update", "get_current_version"]),
    ("tools.license", ["get_license_info"]),
    ("tools.computer_settings", [
        "set_volume", "get_audio_level", "mute_audio",
        "set_brightness", "get_brightness", "wifi_toggle",
    ]),
    ("tools.screen_vision", ["analyze_screen"]),
    ("tools.youtube_tool", ["open_youtube", "search_youtube", "play_music"]),
    ("tools.code_tools", ["write_code", "run_code", "explain_code"]),
    ("tools.flight_finder", ["search_flights"]),
    ("tools.planner", ["create_plan"]),
    ("tools.games", [
        "open_steam", "open_epic_games", "list_installed_steam_games",
        "launch_game_steam", "search_game_on_steam", "install_game_steam",
    ]),
]

TOOL_FUNCTIONS = {}
for _module_name, _tool_names in _TOOL_MODULES:
    _module = importlib.import_module(_module_name)
    for _tool_name in _tool_names:
        TOOL_FUNCTIONS[_tool_name] = getattr(_module, _tool_name)
