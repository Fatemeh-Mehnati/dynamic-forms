# Create your tests here.

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Category, Choice, Form, Question
from .serializers import QuestionSerializer

User = get_user_model()

class QuestionSerializerTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="question_user",
            password="testpass123",
        )
        self.form = Form.objects.create(
            owner=self.user,
            title="Test Form",
            description="Form for question tests",
            is_public=True,
        )

    def test_create_text_question(self):
        serializer = QuestionSerializer(
            data={
                "form": self.form.id,
                "type": Question.TYPE_TEXT,
                "text": "What is your name?",
                "is_required": True,
                "order": 1,
                "config": {
                    "min_length": 2,
                    "max_length": 50,
                },
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        question = serializer.save(form=self.form)

        self.assertEqual(question.type, Question.TYPE_TEXT)
        self.assertEqual(question.config["min_length"], 2)

    def test_create_number_question(self):
        serializer = QuestionSerializer(
            data={
                "form": self.form.id,
                "type": Question.TYPE_NUMBER,
                "text": "How old are you?",
                "order": 2,
                "config": {
                    "min": 1,
                    "max": 100,
                },
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        question = serializer.save(form=self.form)

        self.assertEqual(question.type, Question.TYPE_NUMBER)
        self.assertEqual(question.config["max"], 100)

    def test_select_question_requires_two_choices(self):
        serializer = QuestionSerializer(
            data={
                "form": self.form.id,
                "type": Question.TYPE_SELECT,
                "text": "Choose one",
                "order": 3,
                "config": {},
                "choices": [
                    {"label": "Option A", "order": 1},
                ],
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("choices", serializer.errors)

    def test_select_question_with_two_choices(self):
        serializer = QuestionSerializer(
            data={
                "form": self.form.id,
                "type": Question.TYPE_SELECT,
                "text": "Choose one",
                "order": 4,
                "config": {},
                "choices": [
                    {"label": "Option A", "order": 1},
                    {"label": "Option B", "order": 2},
                ],
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        question = serializer.save(form=self.form)

        self.assertEqual(
            question.choices.filter(is_active=True).count(),
            2,
        )

    def test_text_config_rejects_invalid_length_range(self):
        serializer = QuestionSerializer(
            data={
                "form": self.form.id,
                "type": Question.TYPE_TEXT,
                "text": "Invalid text question",
                "order": 5,
                "config": {
                    "min_length": 10,
                    "max_length": 5,
                },
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("config", serializer.errors)

    def test_number_config_rejects_invalid_range(self):
        serializer = QuestionSerializer(
            data={
                "form": self.form.id,
                "type": Question.TYPE_NUMBER,
                "text": "Invalid number question",
                "order": 6,
                "config": {
                    "min": 20,
                    "max": 10,
                },
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("config", serializer.errors)


class QuestionAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="question_api_user",
            password="testpass123",
        )
        self.other_user = User.objects.create_user(
            username="other_question_api_user",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

        self.form = Form.objects.create(
            owner=self.user,
            title="Question API Form",
            description="Form for API tests",
            is_public=True,
        )
        self.other_form = Form.objects.create(
            owner=self.other_user,
            title="Other Form",
            description="Form owned by another user",
            is_public=True,
        )

        self.list_url = (
            f"/api/v1/forms/{self.form.id}/questions/"
        )

    def test_create_question(self):
        response = self.client.post(
            self.list_url,
            {
                "type": Question.TYPE_TEXT,
                "text": "What is your name?",
                "is_required": True,
                "order": 1,
                "config": {"min_length": 2},
            },
            format="json",
        )
        print(response.data)

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertTrue(
            Question.objects.filter(
                form=self.form,
                text="What is your name?",
            ).exists()
        )

    def test_list_questions(self):
        Question.objects.create(
            form=self.form,
            type=Question.TYPE_TEXT,
            text="Question 1",
            order=1,
        )
        Question.objects.create(
            form=self.form,
            type=Question.TYPE_TEXT,
            text="Question 2",
            order=2,
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_cannot_access_other_users_form_questions(self):
        url = (
            f"/api/v1/forms/{self.other_form.id}/questions/"
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
    def test_update_question(self):
        question = Question.objects.create(
            form=self.form,
            type=Question.TYPE_TEXT,
            text="Old question",
            order=1,
        )
        detail_url = f"{self.list_url}{question.id}/"

        response = self.client.patch(
            detail_url,
            {"text": "Updated question"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        question.refresh_from_db()
        self.assertEqual(question.text, "Updated question")


    def test_soft_delete_question(self):
        question = Question.objects.create(
            form=self.form,
            type=Question.TYPE_SELECT,
            text="Choose an option",
            order=1,
        )
        Choice.objects.create(
            question=question,
            label="Option A",
            order=1,
        )
        Choice.objects.create(
            question=question,
            label="Option B",
            order=2,
        )

        detail_url = f"{self.list_url}{question.id}/"

        response = self.client.delete(detail_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        question.refresh_from_db()
        self.assertFalse(question.is_active)
        self.assertEqual(
            question.choices.filter(is_active=True).count(),
            0,
        )

    
    def test_update_question_choices(self):
        question = Question.objects.create(
            form=self.form,
            type=Question.TYPE_SELECT,
            text="Choose an option",
            order=1,
        )
        choice_a = Choice.objects.create(
            question=question,
            label="Option A",
            order=1,
        )
        choice_b = Choice.objects.create(
            question=question,
            label="Option B",
            order=2,
        )

        detail_url = f"{self.list_url}{question.id}/"

        response = self.client.patch(
            detail_url,
            {
                "choices": [
                    {
                        "id": choice_a.id,
                        "label": "Updated Option A",
                        "order": 1,
                    },
                    {
                        "label": "Option C",
                        "order": 2,
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        choice_a.refresh_from_db()
        choice_b.refresh_from_db()

        self.assertEqual(choice_a.label, "Updated Option A")
        self.assertFalse(choice_b.is_active)
        self.assertTrue(
            question.choices.filter(
                label="Option C",
                is_active=True,
            ).exists()
        )
        self.assertEqual(
            question.choices.filter(is_active=True).count(),
            2,
        )
    def test_update_question_rejects_invalid_choice_id(self):
        question = Question.objects.create(
            form=self.form,
            type=Question.TYPE_SELECT,
            text="Choose an option",
            order=1,
        )
        Choice.objects.create(
            question=question,
            label="Option A",
            order=1,
        )
        Choice.objects.create(
            question=question,
            label="Option B",
            order=2,
        )

        detail_url = f"{self.list_url}{question.id}/"

        response = self.client.patch(
            detail_url,
            {
                "choices": [
                    {
                        "id": 99999,
                        "label": "Invalid option",
                        "order": 1,
                    },
                    {
                        "label": "Option C",
                        "order": 2,
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
    def test_changing_question_type_deactivates_choices(self):
        question = Question.objects.create(
            form=self.form,
            type=Question.TYPE_SELECT,
            text="Choose an option",
            order=1,
        )
        Choice.objects.create(
            question=question,
            label="Option A",
            order=1,
        )
        Choice.objects.create(
            question=question,
            label="Option B",
            order=2,
        )

        detail_url = f"{self.list_url}{question.id}/"

        response = self.client.patch(
            detail_url,
            {"type": Question.TYPE_TEXT},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        question.refresh_from_db()

        self.assertEqual(question.type, Question.TYPE_TEXT)
        self.assertEqual(
            question.choices.filter(is_active=True).count(),
            0,
        )


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

class PublicFormAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="public_form_user",
            password="testpass123",
        )

        self.public_form = Form.objects.create(
            owner=self.user,
            title="Public Survey",
            description="Public form description",
            is_public=True,
        )

        self.private_form = Form.objects.create(
            owner=self.user,
            title="Private Survey",
            description="Private form description",
            is_public=False,
        )
        self.private_form.set_password("secret123")
        self.private_form.save()

        self.public_url = (
            f"/api/v1/public/forms/{self.public_form.slug}/"
        )
        self.private_url = (
            f"/api/v1/public/forms/{self.private_form.slug}/"
        )
        self.access_url = f"{self.private_url}access/"

    def test_get_public_form(self):
        question = Question.objects.create(
            form=self.public_form,
            type=Question.TYPE_TEXT,
            text="Your name?",
            order=1,
            is_active=True,
        )

        response = self.client.get(self.public_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Public Survey")
        self.assertEqual(len(response.data["questions"]), 1)
        self.assertEqual(
            response.data["questions"][0]["id"],
            question.id,
        )

    def test_public_form_excludes_inactive_questions(self):
        Question.objects.create(
            form=self.public_form,
            type=Question.TYPE_TEXT,
            text="Active question",
            order=1,
            is_active=True,
        )
        Question.objects.create(
            form=self.public_form,
            type=Question.TYPE_TEXT,
            text="Inactive question",
            order=2,
            is_active=False,
        )

        response = self.client.get(self.public_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["questions"]), 1)
        self.assertEqual(
            response.data["questions"][0]["text"],
            "Active question",
        )

    def test_public_form_excludes_inactive_choices(self):
        question = Question.objects.create(
            form=self.public_form,
            type=Question.TYPE_SELECT,
            text="Choose a color",
            order=1,
        )

        Choice.objects.create(
            question=question,
            label="Red",
            order=1,
            is_active=True,
        )
        Choice.objects.create(
            question=question,
            label="Blue",
            order=2,
            is_active=False,
        )

        response = self.client.get(self.public_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        choices = response.data["questions"][0]["choices"]
        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0]["label"], "Red")

    def test_private_form_without_token_is_forbidden(self):
        response = self.client.get(self.private_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_private_form_rejects_wrong_password(self):
        response = self.client.post(
            self.access_url,
            {"password": "wrong-password"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_private_form_accepts_correct_password(self):
        response = self.client.post(
            self.access_url,
            {"password": "secret123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)

    def test_private_form_accepts_valid_token(self):
        access_response = self.client.post(
            self.access_url,
            {"password": "secret123"},
            format="json",
        )
        token = access_response.data["access_token"]

        response = self.client.get(
            self.private_url,
            HTTP_X_FORM_ACCESS_TOKEN=token,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Private Survey")