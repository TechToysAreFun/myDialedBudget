from application import app, nav_avatar

@app.context_processor
def context_processor():
    return dict(avatar_key=nav_avatar)
