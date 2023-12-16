from rest_framework import permissions

class HasExpenditureMethod(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True

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