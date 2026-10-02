# Create your tests here.

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Category, Form

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


class FormAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="form_user",
            password="testpass123",
        )
        self.other_user = User.objects.create_user(
            username="other_form_user",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)
        self.list_url = "/api/v1/forms/"

    def test_create_public_form(self):
        response = self.client.post(
            self.list_url,
            {
                "title": "Fitness Survey",
                "description": "A public fitness survey",
                "is_public": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertTrue(
            Form.objects.filter(
                owner=self.user,
                title="Fitness Survey",
                is_public=True,
            ).exists()
        )
        self.assertNotIn("password_hash", response.data)
        self.assertEqual(
            response.data["response_url"],
            f"/api/v1/public/forms/{response.data['slug']}/submissions/",
        )
    
    def test_create_private_form_with_password(self):
        response = self.client.post(
            self.list_url,
            {
                "title": "Private Survey",
                "description": "A private survey",
                "is_public": False,
                "password": "secret123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        form = Form.objects.get(
            owner=self.user,
            title="Private Survey",
        )

        self.assertTrue(form.check_password("secret123"))
        self.assertNotEqual(form.password_hash, "secret123")
        self.assertNotIn("password_hash", response.data)
        self.assertNotIn("password", response.data)

    def test_create_private_form_without_password(self):
        response = self.client.post(
            self.list_url,
            {
                "title": "Private Survey",
                "description": "A private survey",
                "is_public": False,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("password", response.data["error"]["details"])

    def test_user_cannot_access_other_users_form(self):
        form = Form.objects.create(
            owner=self.other_user,
            title="Other User Form",
            description="A private form",
            is_public=False,
        )
        form.set_password("secret123")
        form.save()

        detail_url = f"{self.list_url}{form.pk}/"
        response = self.client.get(detail_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
    
    def test_list_only_own_forms(self):
        Form.objects.create(
            owner=self.user,
            title="My Form",
            description="My own form",
            is_public=True,
        )
        Form.objects.create(
            owner=self.other_user,
            title="Other Form",
            description="Another user's form",
            is_public=True,
        )

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "My Form")

    def test_update_own_form(self):
        form = Form.objects.create(
            owner=self.user,
            title="Old Title",
            description="Old description",
            is_public=True,
        )

        detail_url = f"{self.list_url}{form.pk}/"
        response = self.client.patch(
            detail_url,
            {"title": "Updated Title"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        form.refresh_from_db()
        self.assertEqual(form.title, "Updated Title")

    
    def test_delete_own_form(self):
        form = Form.objects.create(
            owner=self.user,
            title="Form to Delete",
            description="This form will be deleted",
            is_public=True,
        )

        detail_url = f"{self.list_url}{form.pk}/"
        response = self.client.delete(detail_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            Form.objects.filter(pk=form.pk).exists()
        )
    
    def test_search_forms_by_title(self):
        Form.objects.create(
            owner=self.user,
            title="Fitness Survey",
            description="A survey about exercise",
            is_public=True,
        )
        Form.objects.create(
            owner=self.user,
            title="Nutrition Survey",
            description="A survey about diet",
            is_public=True,
        )
        Form.objects.create(
            owner=self.other_user,
            title="Fitness Plan",
            description="Another user's form",
            is_public=True,
        )

        response = self.client.get(
            self.list_url,
            {"search": "Fitness"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["title"],
            "Fitness Survey",
        )
    
    def test_filter_forms_by_category(self):
        category = Category.objects.create(
            owner=self.user,
            name="Fitness",
        )
        other_category = Category.objects.create(
            owner=self.user,
            name="Nutrition",
        )

        Form.objects.create(
            owner=self.user,
            category=category,
            title="Fitness Form",
            description="Fitness details",
            is_public=True,
        )
        Form.objects.create(
            owner=self.user,
            category=other_category,
            title="Nutrition Form",
            description="Nutrition details",
            is_public=True,
        )

        response = self.client.get(
            self.list_url,
            {"category": category.id},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["title"],
            "Fitness Form",
        )
