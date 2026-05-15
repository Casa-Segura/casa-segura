from rest_framework import serializers


class PaginationDataSerializer(serializers.Serializer):
    previousPage = serializers.CharField(allow_null=True, read_only=True)
    nextPage = serializers.CharField(allow_null=True, read_only=True)
    currentPage = serializers.IntegerField(read_only=True)
    totalPages = serializers.IntegerField(read_only=True)
    totalItemsOnPage = serializers.IntegerField(read_only=True)
    totalItems = serializers.IntegerField(read_only=True)
    pageSize = serializers.IntegerField(read_only=True)


class ErrorResponseSerializer(serializers.Serializer):
    errors = serializers.ListField(child=serializers.DictField(), read_only=True)
    data = serializers.DictField(allow_null=True, read_only=True)
    meta = serializers.DictField(read_only=True)


class SuccessResponseSerializer(serializers.Serializer):
    message = serializers.CharField(read_only=True)
