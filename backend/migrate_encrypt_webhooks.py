"""
数据迁移脚本：加密现有的 Webhook URL

使用方法：
1. 确保 .env 文件中已配置 ENCRYPTION_KEY
2. 在 backend 目录下运行：python migrate_encrypt_webhooks.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from app.core.database import get_async_session_context
from app.models.models import Family
from app.core.encryption import encrypt_sensitive_data, decrypt_sensitive_data


async def migrate_webhooks():
    """迁移所有明文 webhook URL 到加密格式"""
    
    print("开始迁移 Webhook URLs...")
    
    migrated_count = 0
    skipped_count = 0
    error_count = 0
    
    async with get_async_session_context() as db:
        # 获取所有有 webhook URL 的家庭
        result = await db.execute(
            select(Family).where(Family.wechat_webhook_url.isnot(None))
        )
        families = result.scalars().all()
        
        print(f"找到 {len(families)} 个家庭有 Webhook URL 配置")
        
        for family in families:
            try:
                # 尝试解密，如果能成功解密说明已经是加密格式
                try:
                    decrypted = decrypt_sensitive_data(family.wechat_webhook_url)
                    print(f"✓ 家庭 {family.id} ({family.name}) 的 Webhook 已经是加密格式，跳过")
                    skipped_count += 1
                    continue
                except Exception:
                    # 解密失败，说明是明文，需要加密
                    pass
                
                # 检查是否是有效的 webhook URL
                if not family.wechat_webhook_url.startswith("https://qyapi.weixin.qq.com/"):
                    print(f"⚠ 家庭 {family.id} ({family.name}) 的 Webhook URL 格式无效，跳过: {family.wechat_webhook_url[:50]}...")
                    skipped_count += 1
                    continue
                
                # 加密并更新
                original_url = family.wechat_webhook_url
                encrypted_url = encrypt_sensitive_data(original_url)
                family.wechat_webhook_url = encrypted_url
                
                print(f"✓ 家庭 {family.id} ({family.name}) 的 Webhook 已加密")
                migrated_count += 1
                
                # 验证加密是否正确
                verified = decrypt_sensitive_data(encrypted_url)
                if verified != original_url:
                    raise ValueError("加密验证失败！解密后的值与原始值不匹配")
                
            except Exception as e:
                print(f"✗ 处理家庭 {family.id} ({family.name}) 时出错: {str(e)}")
                error_count += 1
        
        # 提交所有更改
        if migrated_count > 0:
            await db.commit()
            print(f"\n✓ 已提交 {migrated_count} 个加密更新到数据库")
        else:
            print("\n没有需要迁移的数据")
    
    print("\n" + "="*60)
    print("迁移完成！")
    print(f"  成功加密: {migrated_count} 个")
    print(f"  已跳过: {skipped_count} 个")
    print(f"  错误: {error_count} 个")
    print("="*60)
    
    return migrated_count, skipped_count, error_count


async def verify_migration():
    """验证迁移结果"""
    
    print("\n开始验证迁移...")
    
    async with get_async_session_context() as db:
        result = await db.execute(
            select(Family).where(Family.wechat_webhook_url.isnot(None))
        )
        families = result.scalars().all()
        
        all_valid = True
        for family in families:
            try:
                # 尝试解密
                decrypted = decrypt_sensitive_data(family.wechat_webhook_url)
                if not decrypted.startswith("https://qyapi.weixin.qq.com/"):
                    print(f"✗ 家庭 {family.id} ({family.name}) 解密后的 URL 格式无效")
                    all_valid = False
                else:
                    print(f"✓ 家庭 {family.id} ({family.name}) 验证通过")
            except Exception as e:
                print(f"✗ 家庭 {family.id} ({family.name}) 验证失败: {str(e)}")
                all_valid = False
        
        if all_valid:
            print("\n✓ 所有 Webhook URL 验证通过！")
        else:
            print("\n✗ 部分 Webhook URL 验证失败，请检查！")
        
        return all_valid


async def main():
    """主函数"""
    
    print("="*60)
    print("Webhook URL 加密迁移工具")
    print("="*60)
    
    try:
        # 执行迁移
        migrated, skipped, errors = await migrate_webhooks()
        
        # 如果有成功迁移的，进行验证
        if migrated > 0:
            await verify_migration()
        
        if errors > 0:
            print("\n⚠ 迁移过程中出现错误，请检查日志")
            sys.exit(1)
        else:
            print("\n✓ 迁移成功完成！")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n✗ 迁移失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
