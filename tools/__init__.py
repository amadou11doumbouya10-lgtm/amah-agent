from tools.files            import list_files, organize_folder, find_files, move_file, create_folder, read_file, get_folder_info
from tools.documents   import create_word, create_txt, create_pdf, read_document
from tools.search      import web_search, read_webpage
from tools.system      import get_system_info, open_file, run_command
from tools.memory      import save_memory, get_memories, delete_memory, save_message, load_recent_messages
from tools.email_tool  import read_emails, send_email, search_emails
from tools.browser     import open_browser, click_element, fill_form, take_screenshot, get_page_text
from tools.voice       import speak
from tools.notifications import send_notification, set_reminder
from tools.excel       import read_excel, create_excel, append_to_excel
from tools.clipboard   import read_clipboard, write_clipboard
from tools.utils       import calculate, get_datetime, add_days, generate_password, convert_units
from tools.archive     import zip_files, unzip_file, list_archive
from tools.image_tool        import screenshot_full, resize_image, get_image_info, convert_image, list_processes, get_network_info
from tools.meteo             import get_weather, get_weather_simple
from tools.translator        import translate, detect_language
from tools.qrcode_tool       import create_qrcode
from tools.voice_recognition import listen, listen_continuous
from tools.scheduler         import create_daily_task, list_tasks, delete_task, run_task_now
from tools.stats             import get_stats, reset_stats
from tools.updater           import check_update, get_current_version
from tools.license           import get_license_info

TOOL_FUNCTIONS = {
    "list_files":        list_files,
    "organize_folder":   organize_folder,
    "find_files":        find_files,
    "move_file":         move_file,
    "create_folder":     create_folder,
    "read_file":         read_file,
    "get_folder_info":   get_folder_info,
    "create_word":       create_word,
    "create_txt":        create_txt,
    "create_pdf":        create_pdf,
    "read_document":     read_document,
    "web_search":        web_search,
    "read_webpage":      read_webpage,
    "get_system_info":   get_system_info,
    "open_file":         open_file,
    "run_command":       run_command,
    "save_memory":       save_memory,
    "get_memories":      get_memories,
    "delete_memory":     delete_memory,
    "read_emails":       read_emails,
    "send_email":        send_email,
    "search_emails":     search_emails,
    "open_browser":      open_browser,
    "click_element":     click_element,
    "fill_form":         fill_form,
    "take_screenshot":   take_screenshot,
    "get_page_text":     get_page_text,
    "speak":             speak,
    "send_notification": send_notification,
    "set_reminder":      set_reminder,
    "read_excel":        read_excel,
    "create_excel":      create_excel,
    "append_to_excel":   append_to_excel,
    "read_clipboard":    read_clipboard,
    "write_clipboard":   write_clipboard,
    "calculate":         calculate,
    "get_datetime":      get_datetime,
    "add_days":          add_days,
    "generate_password": generate_password,
    "convert_units":     convert_units,
    "zip_files":         zip_files,
    "unzip_file":        unzip_file,
    "list_archive":      list_archive,
    "screenshot_full":   screenshot_full,
    "resize_image":      resize_image,
    "get_image_info":    get_image_info,
    "convert_image":     convert_image,
    "list_processes":      list_processes,
    "get_network_info":    get_network_info,
    "get_weather":         get_weather,
    "get_weather_simple":  get_weather_simple,
    "translate":           translate,
    "detect_language":     detect_language,
    "create_qrcode":       create_qrcode,
    "listen":              listen,
    "listen_continuous":   listen_continuous,
    "create_daily_task":   create_daily_task,
    "list_tasks":          list_tasks,
    "delete_task":         delete_task,
    "run_task_now":        run_task_now,
    "get_stats":           get_stats,
    "reset_stats":         reset_stats,
    "check_update":        check_update,
    "get_current_version": get_current_version,
    "get_license_info":    get_license_info,
}
