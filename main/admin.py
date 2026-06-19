from django.contrib import admin
from .models import User, ServiceStation, Car, Service, Review

admin.site.register(User)
admin.site.register(ServiceStation)
admin.site.register(Car)
admin.site.register(Service)
admin.site.register(Review)