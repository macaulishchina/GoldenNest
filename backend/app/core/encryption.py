"""
小金库 (Golden Nest) - 加密工具
用于敏感数据的加密和解密
"""
from cryptography.fernet import Fernet
from app.core.config import settings


class EncryptionService:
    """加密服务"""
    
    def __init__(self):
        """初始化加密服务"""
        self.fernet = None
        
        if settings.ENCRYPTION_KEY:
            try:
                self.fernet = Fernet(settings.ENCRYPTION_KEY.encode())
            except Exception as e:
                import logging
                logging.warning(f"Invalid ENCRYPTION_KEY, encryption disabled: {e}")
                self.fernet = None
        else:
            import logging
            logging.info("ENCRYPTION_KEY not configured, sensitive data will be stored in plaintext")
    
    def encrypt(self, plaintext: str) -> str:
        """
        加密字符串
        
        Args:
            plaintext: 明文字符串
            
        Returns:
            加密后的字符串（Base64编码），如果未配置密钥则返回明文
        """
        if not plaintext:
            return plaintext
        
        # 如果没有配置加密，直接返回明文
        if self.fernet is None:
            return plaintext
        
        try:
            encrypted_bytes = self.fernet.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            import logging
            logging.error(f"Encryption failed: {e}")
            return plaintext
    
    def decrypt(self, encrypted_text: str) -> str:
        """
        解密字符串
        
        Args:
            encrypted_text: 加密的字符串
            
        Returns:
            解密后的明文字符串，如果未配置密钥则返回原文
        """
        if not encrypted_text:
            return encrypted_text
        
        # 如果没有配置加密，直接返回原文
        if self.fernet is None:
            return encrypted_text
        
        try:
            decrypted_bytes = self.fernet.decrypt(encrypted_text.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            # 如果解密失败，可能是未加密的数据，直接返回原文
            import logging
            logging.warning(f"Decryption failed, returning original text: {e}")
            return encrypted_text


# 全局加密服务实例
_encryption_service = None


def get_encryption_service() -> EncryptionService:
    """获取加密服务单例"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def encrypt_sensitive_data(data: str) -> str:
    """快捷方法：加密敏感数据"""
    return get_encryption_service().encrypt(data)


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """快捷方法：解密敏感数据"""
    return get_encryption_service().decrypt(encrypted_data)


def generate_encryption_key() -> str:
    """
    生成新的加密密钥
    
    Returns:
        Base64编码的Fernet密钥
        
    Usage:
        from app.core.encryption import generate_encryption_key
        key = generate_encryption_key()
        print(f"ENCRYPTION_KEY={key}")
    """
    return Fernet.generate_key().decode()


if __name__ == "__main__":
    # 生成新密钥的脚本
    print("🔐 生成新的加密密钥：")
    print(f"ENCRYPTION_KEY={generate_encryption_key()}")
    print("\n📝 请将此密钥添加到 .env 文件中")
    print("⚠️  密钥丢失将无法解密已加密的数据！请妥善保管")
