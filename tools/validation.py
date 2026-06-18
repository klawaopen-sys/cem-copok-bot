import os
import config

def validate_image_path(image_rel_path: str, name: str):
    """Validate that the image file exists relative to the project root.
    Args:
        image_rel_path: Relative path to the image (e.g., '.tmp/focus_default.jpg')
        name: Human‑readable name for logging.
    Returns:
        bool indicating existence.
    """
    project_root = os.path.dirname(os.path.abspath(__file__))
    # Assuming this file resides in tools/, go one level up to project root
    project_root = os.path.abspath(os.path.join(project_root, '..'))
    image_path = os.path.join(project_root, image_rel_path)
    if os.path.exists(image_path):
        print(f"✅ {name} image found at {image_path}")
        return True
    else:
        print(f"⚠️ {name} image NOT found at {image_path}!"
              f" Please ensure the file exists or update config.{name.upper()}_IMAGE.")
        return False

def validate_required_images():
    """Check that all permanent images for scheduled posts exist.
    This is called at startup to warn about missing assets before the bot runs.
    """
    focus_ok = validate_image_path(getattr(config, 'FOCUS_IMAGE', '.tmp/focus_default.jpg'), 'focus')
    daily_ok = validate_image_path(getattr(config, 'DAILY_UPGRADE_IMAGE', '.tmp/daily_upgrade.jpg'), 'daily upgrade')
    return focus_ok and daily_ok
