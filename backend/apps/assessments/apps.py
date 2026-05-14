from django.apps import AppConfig

#这个文件是Django应用的配置文件，定义了AssessmentsConfig类，继承自AppConfig。它指定了默认的自动字段类型为BigAutoField，并设置了应用的名称为'apps.assessments'。这个配置类会在Django项目中被自动识别和使用，以便正确地配置和管理这个应用。
class AssessmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.assessments'
