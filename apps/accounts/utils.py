import re

def validate_password_strength(password):
    score = 0
    requirements = {
        'length': len(password) >= 8,
        'uppercase': bool(re.search(r'[A-Z]', password)),
        'lowercase': bool(re.search(r'[a-z]', password)),
        'digit': bool(re.search(r'\d', password)),
        'special': bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password)),
    }
    score = sum(requirements.values())
    # Calculate percentage for the progress bar
    percent = score * 20   # 0 to 100
    if percent > 100:
        percent = 100
    if score <= 2:
        strength = 'weak'
    elif score == 3:
        strength = 'fair'
    elif score == 4:
        strength = 'good'
    else:
        strength = 'strong'
    return {
        'score': score,
        'strength': strength,
        'requirements': requirements,
        'percent': percent,
    }