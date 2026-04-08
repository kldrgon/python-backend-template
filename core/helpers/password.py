import bcrypt


def hash_password(password: str) -> str:
    """
    使用bcrypt对密码进行hash
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    # 生成salt并hash密码
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """
    验证密码是否匹配
    """
    if not password or not hashed_password:
        return False
    
    return bcrypt.checkpw(
        password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )
