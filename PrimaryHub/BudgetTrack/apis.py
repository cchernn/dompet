from rest_framework import views, response, permissions, status
from .serializers import ExpenditureSerializer
from . import services

class ExpenditureCreateAPI(views.APIView):
    permission_classes = (permissions.IsAuthenticated, )

    def post(self, request):
        serializer = ExpenditureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        serializer.instance = services.create_expenditure(expendituredc=data)

        return response.Response(data=serializer.data)
        

    def get(self, request):
        # expenditure_collection = services.get_expenditure(user)
        expenditure_collection = services.get_expenditure()
        serializer = ExpenditureSerializer(expenditure_collection, many=True)

        return response.Response(data=serializer.data)

class ExpenditureRetrieveUpdateDeleteAPI(views.APIView):
    permission_classes = (permissions.IsAuthenticated, )

    def get(self, request, expenditure_id):
        expenditure = services.get_expenditure_detail(expenditure_id=expenditure_id)
        serializer = ExpenditureSerializer(expenditure)

        return response.Response(data=serializer.data)
    
    def delete(self, request, expenditure_id):
        services.delete_expenditure(expenditure_id=expenditure_id)

        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def put(self, request, expenditure_id):
        expenditure = services.get_expenditure_detail(expenditure_id=expenditure_id)

        serializer = ExpenditureSerializer(expenditure, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        expenditure = serializer.validated_data
        serializer.instance = services.update_expenditure(expenditure_id=expenditure_id, expenditure_data=expenditure)

        return response.Response(data=serializer.data)
    