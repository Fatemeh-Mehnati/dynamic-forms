# Create your tests here.

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Category

User = get_user_model()


class CategoryAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user1",
            password="testpass123",
        )
        self.other_user = User.objects.create_user(
            username="user2",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)
        self.list_url = "/api/v1/categories/"

    def test_create_category(self):
        response = self.client.post(
            self.list_url,
            {"name": "Fitness"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Category.objects.filter(owner=self.user, name="Fitness").exists()
        )

    def test_list_only_own_categories(self):
        Category.objects.create(owner=self.user, name="Fitness")
        Category.objects.create(owner=self.other_user, name="Nutrition")

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Fitness")

    def test_duplicate_category_name(self):
        Category.objects.create(owner=self.user, name="Fitness")

        response = self.client.post(
            self.list_url,
            {"name": "Fitness"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_cannot_access_other_users_category(self):
        category = Category.objects.create(
            owner=self.other_user,
            name="Nutrition",
        )
        detail_url = f"{self.list_url}{category.pk}/"

        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_category(self):
        category = Category.objects.create(owner=self.user, name="Fitness")
        detail_url = f"{self.list_url}{category.pk}/"

        response = self.client.delete(detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())