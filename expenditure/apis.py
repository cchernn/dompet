from rest_framework import views, response, permissions, status
from .serializers import ExpenditureSerializer, ExpenditureGroupSerializer
from .permissions import HasExpenditureMethod
from . import services

class ExpenditureCreateAPI(views.APIView):
    permission_classes = [permissions.IsAuthenticated, HasExpenditureMethod]

    def post(self, request, expenditure_group_id):
        serializer = ExpenditureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        serializer.instance = services.create_expenditure(group_id=expenditure_group_id, user=request.user, expendituredc=data)

        return response.Response(data=serializer.data)

    def get(self, request, expenditure_group_id):
        expenditure_collection = services.get_expenditure(group_id=expenditure_group_id)
        serializer = ExpenditureSerializer(expenditure_collection, many=True)

        return response.Response(data=serializer.data)

class ExpenditureRetrieveUpdateDeleteAPI(views.APIView):
    permission_classes = [permissions.IsAuthenticated, HasExpenditureMethod]

    def get(self, request, expenditure_group_id, expenditure_id):
        expenditure = services.get_expenditure_detail(group_id=expenditure_group_id, expenditure_id=expenditure_id)
        serializer = ExpenditureSerializer(expenditure)

        return response.Response(data=serializer.data)

    def delete(self, request, expenditure_group_id, expenditure_id):
        services.delete_expenditure(user=request.user, group_id=expenditure_group_id, expenditure_id=expenditure_id)

        return response.Response(status=status.HTTP_204_NO_CONTENT)
    
    def put(self, request, expenditure_group_id, expenditure_id):
        expenditure = services.get_expenditure_detail(group_id=expenditure_group_id, expenditure_id=expenditure_id)

        serializer = ExpenditureSerializer(expenditure, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        expenditure = serializer.validated_data
        serializer.instance = services.update_expenditure(user=request.user, group_id=expenditure_group_id, expenditure_id=expenditure_id, expenditure_data=expenditure)

        return response.Response(data=serializer.data)
    
class ExpenditureGroupCreateAPI(views.APIView):
    permission_classes = [permissions.IsAuthenticated, HasExpenditureMethod]

    def post(self, request):
        serializer = ExpenditureGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        serializer.instance = services.create_expenditure_group(user=request.user, expendituregroupdc=data)

        return response.Response(data=serializer.data)

    def get(self, request):
        expenditure_group_collection = services.get_expenditure_group(user=request.user)
        serializer = ExpenditureGroupSerializer(expenditure_group_collection, many=True)

        return response.Response(data=serializer.data)
    
class ExpenditureGroupRetrieveUpdateDeleteAPI(views.APIView):
    permission_classes = [permissions.IsAuthenticated, HasExpenditureMethod]

    def get(self, request, expenditure_group_id):
        expenditure_group = services.get_expenditure_group_detail(user=request.user, expenditure_group_id=expenditure_group_id)
        serializer = ExpenditureGroupSerializer(expenditure_group)

        return response.Response(data=serializer.data)

    def delete(self, request, expenditure_group_id):
        services.delete_expenditure_group(user=request.user, expenditure_group_id=expenditure_group_id)

        return response.Response(status=status.HTTP_204_NO_CONTENT)
    
    def put(self, request, expenditure_group_id):
        expenditure_group = services.get_expenditure_group_detail(user=request.user, expenditure_group_id=expenditure_group_id)

        serializer = ExpenditureGroupSerializer(expenditure_group, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        expenditure_group = serializer.validated_data
        serializer.instance = services.update_expenditure_group(user=request.user, expenditure_group_id=expenditure_group_id, expenditure_group_data=expenditure_group)

        return response.Response(data=serializer.data)