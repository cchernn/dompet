from rest_framework import permissions
from .models import ExpenditureGroup

class HasExpenditureMethod(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True

        if not self.has_expenditure_group_permission(request=request, view=view):
            return False

        if request.method == "GET":
            return request.user.has_perm("expenditure.view_expenditure")
    
        if request.method == "POST":
            return request.user.has_perm("expenditure.add_expenditure")
        
        if request.method in ["PUT", "PATCH"]:
            return request.user.has_perm("expenditure.change_expenditure")
        
        if request.method in ["DELETE"]:
            return request.user.has_perm("expenditure.delete_expenditure")

        return False
    
    # def has_object_permission(self, request, view, obj):
    #     return True
    
    def has_expenditure_group_permission(self, request, view):
        group_id = view.kwargs.get('expenditure_group_id')
        if not group_id: #endpoint doesn't involve expenditure_group_id
            return True
        users = ExpenditureGroup.users.through.objects.filter(expendituregroup_id=group_id)
        user_ids = [user.user_id for user in users]
        if request.user.id in user_ids:
            return True
        return False