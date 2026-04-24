# 每个应用必须有 apps.py 来定义配置，这是 Django 应用的"身份证"，让框架知道如何加载和管理这个应用。
from django.apps import AppConfig   #导入 Django 自带的应用配置基类，所有模块都必须继承它。

# 创建一个叫 AccountsConfig 的配置类，对应 accounts（账号 / 用户）模块。
class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'#设置该应用中模型的默认主键字段类型为 BigAutoField（64位整数）。
    name = 'apps.accounts'#指定应用的完整模块路径（相对于项目根目录）。
