from config import settings

print("Application:", settings.app_name)
print("Environment:", settings.app_env)
print("Host:", settings.host)
print("Port:", settings.port)

print("Realtime Model:", settings.openai_realtime_model)
print("Text Model:", settings.openai_text_model)

print("Database:", settings.database_path)
print("Session Timeout:", settings.session_idle_timeout_seconds)

print("Allowed Origins:", settings.allowed_origins)

print("Configuration loaded successfully!")
