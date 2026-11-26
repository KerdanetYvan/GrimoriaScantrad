from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from rest_framework.permissions import IsAuthenticated


@api_view(['GET'])
def health_check(request):
    """
    Health check endpoint to verify that the API is running.
    """
    return Response({'status': 'ok'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    Me request to see who is authenticate
    """
    return Response({'id': request.user.id, 'email': request.user.email})
    