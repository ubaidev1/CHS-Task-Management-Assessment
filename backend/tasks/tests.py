"""RBAC and object-level authorization tests for tasks."""

from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import Role, User
from tasks.models import AssignmentEvent, Task, TaskStatus
from tasks.tasks import send_assignment_notification

# Use an isolated local-memory cache for deterministic cache tests (no shared
# Redis state); the caching *logic* is backend-agnostic.
LOCMEM = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "dashboard-tests",
    }
}


class TaskRBACTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("admin", "admin@e.com", "pw", role=Role.ADMIN)
        cls.manager = User.objects.create_user("manager", "m@e.com", "pw", role=Role.MANAGER)
        cls.emp1 = User.objects.create_user("emp1", "e1@e.com", "pw", role=Role.EMPLOYEE)
        cls.emp2 = User.objects.create_user("emp2", "e2@e.com", "pw", role=Role.EMPLOYEE)
        cls.task1 = Task.objects.create(title="t1", assigned_to=cls.emp1, created_by=cls.manager)
        cls.task2 = Task.objects.create(title="t2", assigned_to=cls.emp2, created_by=cls.manager)
        cls.list_url = reverse("task-list")

    def detail(self, pk):
        return reverse("task-detail", args=[pk])

    # --- visibility (view all vs own) -----------------------------------
    def test_manager_sees_all_tasks(self):
        self.client.force_authenticate(self.manager)
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)

    def test_employee_sees_only_own_tasks(self):
        self.client.force_authenticate(self.emp1)
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["id"], self.task1.id)

    def test_anonymous_is_denied(self):
        self.assertEqual(self.client.get(self.list_url).status_code, 401)

    # --- create (Admin/Manager only) ------------------------------------
    def test_employee_cannot_create_task(self):
        self.client.force_authenticate(self.emp1)
        resp = self.client.post(self.list_url, {"title": "x", "assigned_to": self.emp1.id})
        self.assertEqual(resp.status_code, 403)

    def test_manager_can_create_and_created_by_is_server_set(self):
        self.client.force_authenticate(self.manager)
        resp = self.client.post(self.list_url, {"title": "new", "assigned_to": self.emp1.id})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["created_by"], self.manager.id)
        self.assertEqual(resp.data["assigned_to"], self.emp1.id)

    def test_created_by_cannot_be_spoofed_via_payload(self):
        self.client.force_authenticate(self.manager)
        resp = self.client.post(
            self.list_url,
            {"title": "spoof", "assigned_to": self.emp1.id, "created_by": self.emp2.id},
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["created_by"], self.manager.id)  # payload ignored

    # --- delete (Admin only) --------------------------------------------
    def test_employee_cannot_delete_task(self):
        self.client.force_authenticate(self.emp1)
        self.assertEqual(self.client.delete(self.detail(self.task1.id)).status_code, 403)

    def test_manager_cannot_delete_task(self):
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.delete(self.detail(self.task1.id)).status_code, 403)

    def test_admin_can_delete_task(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.delete(self.detail(self.task1.id)).status_code, 204)

    # --- object-level (IDOR) --------------------------------------------
    def test_employee_cannot_read_another_users_task(self):
        self.client.force_authenticate(self.emp1)
        self.assertEqual(self.client.get(self.detail(self.task2.id)).status_code, 404)

    def test_employee_cannot_update_another_users_task(self):
        self.client.force_authenticate(self.emp1)
        resp = self.client.patch(self.detail(self.task2.id), {"status": TaskStatus.COMPLETED})
        self.assertEqual(resp.status_code, 404)

    # --- field-level (Employee: status only) ----------------------------
    def test_employee_can_update_own_task_status(self):
        self.client.force_authenticate(self.emp1)
        resp = self.client.patch(self.detail(self.task1.id), {"status": TaskStatus.COMPLETED})
        self.assertEqual(resp.status_code, 200)
        self.task1.refresh_from_db()
        self.assertEqual(self.task1.status, TaskStatus.COMPLETED)

    def test_employee_cannot_change_non_status_fields(self):
        self.client.force_authenticate(self.emp1)
        resp = self.client.patch(
            self.detail(self.task1.id),
            {"title": "hacked", "status": TaskStatus.IN_PROGRESS},
        )
        self.assertEqual(resp.status_code, 200)
        self.task1.refresh_from_db()
        self.assertEqual(self.task1.title, "t1")  # title change ignored
        self.assertEqual(self.task1.status, TaskStatus.IN_PROGRESS)  # status applied

    def test_employee_cannot_reassign_own_task(self):
        self.client.force_authenticate(self.emp1)
        self.client.patch(self.detail(self.task1.id), {"assigned_to": self.emp2.id})
        self.task1.refresh_from_db()
        self.assertEqual(self.task1.assigned_to_id, self.emp1.id)  # reassign ignored


@override_settings(CACHES=LOCMEM)
class DashboardCacheTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_user("a", "a@e.com", "pw", role=Role.ADMIN)
        self.emp = User.objects.create_user("e", "e@e.com", "pw", role=Role.EMPLOYEE)
        self.emp2 = User.objects.create_user("e2", "e2@e.com", "pw", role=Role.EMPLOYEE)
        Task.objects.create(title="t1", assigned_to=self.emp, created_by=self.admin,
                            status=TaskStatus.PENDING)
        Task.objects.create(title="t2", assigned_to=self.emp, created_by=self.admin,
                            status=TaskStatus.COMPLETED)
        Task.objects.create(title="t3", assigned_to=self.emp2, created_by=self.admin,
                            status=TaskStatus.PENDING)
        self.url = reverse("dashboard-stats")

    # --- scope -----------------------------------------------------------
    def test_admin_sees_all_tasks_scope(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, {"total_tasks": 3, "completed_tasks": 1,
                                  "pending_tasks": 2, "my_tasks": 0})

    def test_employee_sees_only_own_scope(self):
        self.client.force_authenticate(self.emp)
        r = self.client.get(self.url)
        # For an employee total == my_tasks (same assigned-task scope).
        self.assertEqual(r.data, {"total_tasks": 2, "completed_tasks": 1,
                                  "pending_tasks": 1, "my_tasks": 2})

    def test_anonymous_is_denied(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)

    # --- caching behaviour ----------------------------------------------
    def test_repeated_request_uses_cache(self):
        self.client.force_authenticate(self.emp)
        self.client.get(self.url)  # populate cache
        with self.assertNumQueries(0):  # second request hits cache, no DB
            self.client.get(self.url)

    def test_cache_invalidated_on_task_change(self):
        self.client.force_authenticate(self.emp)
        self.assertEqual(self.client.get(self.url).data["total_tasks"], 2)
        # captureOnCommitCallbacks runs the post-commit invalidation signal.
        with self.captureOnCommitCallbacks(execute=True):
            Task.objects.create(title="t4", assigned_to=self.emp, created_by=self.admin)
        self.assertEqual(self.client.get(self.url).data["total_tasks"], 3)

    def test_cache_is_isolated_per_user(self):
        self.client.force_authenticate(self.emp)
        self.assertEqual(self.client.get(self.url).data["total_tasks"], 2)
        self.client.force_authenticate(self.emp2)
        self.assertEqual(self.client.get(self.url).data["total_tasks"], 1)

    def test_role_change_takes_effect_immediately(self):
        self.client.force_authenticate(self.emp)
        self.assertEqual(self.client.get(self.url).data["total_tasks"], 2)  # employee scope
        self.emp.role = Role.MANAGER
        self.emp.save()
        # New role -> new cache key -> recompute with manager (all-tasks) scope.
        self.assertEqual(self.client.get(self.url).data["total_tasks"], 3)

    def test_redis_outage_falls_back_to_db(self):
        self.client.force_authenticate(self.emp)
        with mock.patch("tasks.stats.cache.get", side_effect=Exception("redis down")), \
             mock.patch("tasks.stats.cache.set", side_effect=Exception("redis down")):
            r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["total_tasks"], 2)  # correct data straight from DB


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class AssignmentNotificationTests(APITestCase):
    def setUp(self):
        self.manager = User.objects.create_user("mgr", "mgr@e.com", "pw", role=Role.MANAGER)
        self.emp1 = User.objects.create_user("e1", "e1@e.com", "pw", role=Role.EMPLOYEE)
        self.emp2 = User.objects.create_user("e2", "e2@e.com", "pw", role=Role.EMPLOYEE)
        self.task = Task.objects.create(title="T", created_by=self.manager)
        self.url = reverse("task-assign", args=[self.task.id])
        mail.outbox = []

    def test_employee_cannot_assign(self):
        self.client.force_authenticate(self.emp1)
        resp = self.client.post(self.url, {"assigned_to": self.emp2.id})
        self.assertEqual(resp.status_code, 403)

    def test_manager_assign_saves_and_queues_notification(self):
        self.client.force_authenticate(self.manager)
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(self.url, {"assigned_to": self.emp1.id})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["queued"])
        self.task.refresh_from_db()
        self.assertEqual(self.task.assigned_to_id, self.emp1.id)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            AssignmentEvent.objects.filter(task=self.task, status="sent").count(), 1
        )

    def test_notification_queued_only_after_commit(self):
        self.client.force_authenticate(self.manager)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(self.url, {"assigned_to": self.emp1.id})
            self.assertEqual(len(mail.outbox), 0)  # not sent while "in transaction"
        self.assertEqual(len(mail.outbox), 1)  # sent only after commit

    def test_assign_to_same_user_is_noop(self):
        self.task.assigned_to = self.emp1
        self.task.save()
        self.client.force_authenticate(self.manager)
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(self.url, {"assigned_to": self.emp1.id})
        self.assertFalse(resp.data["queued"])
        self.assertEqual(AssignmentEvent.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_reassignment_creates_new_event_and_notifies_again(self):
        self.client.force_authenticate(self.manager)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(self.url, {"assigned_to": self.emp1.id})
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(self.url, {"assigned_to": self.emp2.id})
        self.assertEqual(AssignmentEvent.objects.count(), 2)
        self.assertEqual(len(mail.outbox), 2)

    def test_retry_of_same_event_does_not_duplicate(self):
        event = AssignmentEvent.objects.create(
            task=self.task, assigned_to=self.emp1, assigned_by=self.manager
        )
        # Run the task twice for the same event (simulates a Celery re-delivery).
        send_assignment_notification.apply(args=[str(event.id)])
        send_assignment_notification.apply(args=[str(event.id)])
        self.assertEqual(len(mail.outbox), 1)  # exactly one email
        event.refresh_from_db()
        self.assertEqual(event.status, AssignmentEvent.Status.SENT)

    def test_invalid_assignee_is_rejected(self):
        self.client.force_authenticate(self.manager)
        resp = self.client.post(self.url, {"assigned_to": 999999})
        self.assertEqual(resp.status_code, 400)

    def test_creating_task_with_assignee_notifies(self):
        """Creating a task already assigned to someone notifies them (same path)."""
        self.client.force_authenticate(self.manager)
        list_url = reverse("task-list")
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(list_url, {"title": "New", "assigned_to": self.emp1.id})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(AssignmentEvent.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_creating_unassigned_task_sends_no_email(self):
        self.client.force_authenticate(self.manager)
        list_url = reverse("task-list")
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(list_url, {"title": "Unassigned"})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(AssignmentEvent.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)
