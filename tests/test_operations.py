"""
test_operations.py — Unit tests for operations.py CRUD functions.

Uses a temporary SQLite database so tests never touch the real DB file.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import database
import operations
from models import Expense, Budget, User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def in_memory_db(tmp_path, monkeypatch):
    """Redirect every DB call to a fresh temp database for each test."""
    temp_db = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", temp_db)
    database.initialize_db()
    yield


@pytest.fixture
def test_user() -> User:
    """Create and return a fresh test user."""
    return operations.create_user("testuser", "password123", "Test User")


# ---------------------------------------------------------------------------
# Auth / User tests
# ---------------------------------------------------------------------------

class TestCreateUser:
    def test_create_returns_user_with_id(self, test_user):
        assert test_user.id is not None
        assert test_user.id > 0
        assert test_user.username == "testuser"

    def test_duplicate_username_raises(self, test_user):
        with pytest.raises(ValueError, match="already taken"):
            operations.create_user("testuser", "other_pass")

    def test_username_case_insensitive(self, test_user):
        with pytest.raises(ValueError):
            operations.create_user("TESTUSER", "another_pass")


class TestAuthenticateUser:
    def test_correct_credentials_returns_user(self, test_user):
        user = operations.authenticate_user("testuser", "password123")
        assert user is not None
        assert user.id == test_user.id

    def test_wrong_password_returns_none(self, test_user):
        assert operations.authenticate_user("testuser", "wrongpass") is None

    def test_nonexistent_user_returns_none(self):
        assert operations.authenticate_user("nobody", "pass") is None

    def test_case_insensitive_username(self, test_user):
        user = operations.authenticate_user("TESTUSER", "password123")
        assert user is not None


# ---------------------------------------------------------------------------
# Expense CRUD tests
# ---------------------------------------------------------------------------

class TestAddExpense:
    def test_add_returns_valid_id(self, test_user):
        exp = Expense(amount=42.50, category="Food & Dining",
                      description="Lunch", date="2024-03-15", user_id=test_user.id)
        new_id = operations.add_expense(exp)
        assert isinstance(new_id, int) and new_id > 0

    def test_added_expense_retrievable(self, test_user):
        exp = Expense(amount=99.99, category="Transport",
                      description="Uber", date="2024-04-01", user_id=test_user.id)
        new_id = operations.add_expense(exp)
        fetched = operations.get_expense_by_id(new_id)
        assert fetched is not None
        assert fetched.amount == 99.99
        assert fetched.category == "Transport"

    def test_multiple_expenses_increase_count(self, test_user):
        for i in range(5):
            operations.add_expense(
                Expense(amount=10.0 * (i + 1), category="Shopping",
                        description=f"Item {i}", date="2024-05-01", user_id=test_user.id)
            )
        assert len(operations.get_all_expenses(test_user.id)) == 5


class TestGetAllExpenses:
    def test_empty_db_returns_empty_list(self, test_user):
        assert operations.get_all_expenses(test_user.id) == []

    def test_returns_list_of_expense_objects(self, test_user):
        operations.add_expense(
            Expense(amount=5.0, category="Other", description="",
                    date="2024-01-10", user_id=test_user.id)
        )
        result = operations.get_all_expenses(test_user.id)
        assert len(result) == 1
        assert isinstance(result[0], Expense)

    def test_ordered_by_date_descending(self, test_user):
        for d in ("2024-01-01", "2024-03-01", "2024-02-01"):
            operations.add_expense(
                Expense(amount=1.0, category="Other", description="",
                        date=d, user_id=test_user.id)
            )
        result = operations.get_all_expenses(test_user.id)
        dates = [e.date for e in result]
        assert dates == sorted(dates, reverse=True)


class TestUpdateExpense:
    def test_update_changes_fields(self, test_user):
        orig = Expense(amount=10.0, category="Food & Dining",
                       description="Old", date="2024-06-01", user_id=test_user.id)
        new_id = operations.add_expense(orig)
        updated = Expense(id=new_id, amount=25.0, category="Transport",
                          description="New", date="2024-06-15", user_id=test_user.id)
        assert operations.update_expense(updated) is True
        fetched = operations.get_expense_by_id(new_id)
        assert fetched.amount == 25.0
        assert fetched.category == "Transport"

    def test_update_nonexistent_returns_false(self, test_user):
        fake = Expense(id=999, amount=10.0, category="Other",
                       description="", date="2024-01-01", user_id=test_user.id)
        assert operations.update_expense(fake) is False

    def test_update_without_id_returns_false(self, test_user):
        no_id = Expense(amount=10.0, category="Other",
                        description="", date="2024-01-01", user_id=test_user.id)
        assert operations.update_expense(no_id) is False


class TestDeleteExpense:
    def test_delete_removes_record(self, test_user):
        new_id = operations.add_expense(
            Expense(amount=50.0, category="Shopping", description="Shoes",
                    date="2024-07-04", user_id=test_user.id)
        )
        assert operations.delete_expense(new_id) is True
        assert operations.get_expense_by_id(new_id) is None

    def test_delete_nonexistent_returns_false(self):
        assert operations.delete_expense(999) is False

    def test_delete_reduces_count(self, test_user):
        ids = [
            operations.add_expense(
                Expense(amount=1.0, category="Other", description="",
                        date="2024-01-01", user_id=test_user.id)
            )
            for _ in range(3)
        ]
        operations.delete_expense(ids[0])
        assert len(operations.get_all_expenses(test_user.id)) == 2


class TestSearchExpenses:
    @pytest.fixture(autouse=True)
    def seed_data(self, test_user):
        self._uid = test_user.id
        for item in [
            (10.0, "Food & Dining", "2024-01-10"),
            (20.0, "Transport",     "2024-01-20"),
            (50.0, "Food & Dining", "2024-02-05"),
            (5.0,  "Healthcare",    "2024-02-15"),
        ]:
            operations.add_expense(
                Expense(amount=item[0], category=item[1], description="",
                        date=item[2], user_id=self._uid)
            )

    def test_filter_by_category(self):
        results = operations.search_expenses(user_id=self._uid, category="Food & Dining")
        assert all(e.category == "Food & Dining" for e in results)
        assert len(results) == 2

    def test_filter_by_date_range(self):
        results = operations.search_expenses(
            user_id=self._uid, date_from="2024-01-01", date_to="2024-01-31"
        )
        assert len(results) == 2

    def test_filter_by_amount_range(self):
        results = operations.search_expenses(
            user_id=self._uid, amount_min=15.0, amount_max=55.0
        )
        assert all(15.0 <= e.amount <= 55.0 for e in results)

    def test_no_filters_returns_all(self):
        assert len(operations.search_expenses(user_id=self._uid)) == 4

    def test_combined_filters(self):
        results = operations.search_expenses(
            user_id=self._uid, category="Food & Dining", date_from="2024-02-01"
        )
        assert len(results) == 1 and results[0].amount == 50.0


class TestGetExpensesForMonth:
    def test_only_returns_matching_month(self, test_user):
        uid = test_user.id
        operations.add_expense(
            Expense(amount=1.0, category="Other", description="",
                    date="2024-03-01", user_id=uid)
        )
        operations.add_expense(
            Expense(amount=2.0, category="Other", description="",
                    date="2024-04-01", user_id=uid)
        )
        results = operations.get_expenses_for_month(uid, 2024, 3)
        assert len(results) == 1 and results[0].date == "2024-03-01"


# ---------------------------------------------------------------------------
# Budget CRUD tests
# ---------------------------------------------------------------------------

class TestBudgetOperations:
    def test_upsert_inserts_new_budget(self, test_user):
        uid = test_user.id
        operations.upsert_budget(Budget(category="Food & Dining",
                                        monthly_limit=300.0, user_id=uid))
        b = operations.get_budget_for_category(uid, "Food & Dining")
        assert b is not None and b.monthly_limit == 300.0

    def test_upsert_updates_existing_budget(self, test_user):
        uid = test_user.id
        operations.upsert_budget(Budget(category="Transport",
                                        monthly_limit=100.0, user_id=uid))
        operations.upsert_budget(Budget(category="Transport",
                                        monthly_limit=200.0, user_id=uid))
        assert operations.get_budget_for_category(uid, "Transport").monthly_limit == 200.0

    def test_get_all_budgets_returns_all(self, test_user):
        uid = test_user.id
        operations.upsert_budget(Budget(category="Food & Dining",
                                        monthly_limit=300.0, user_id=uid))
        operations.upsert_budget(Budget(category="Transport",
                                        monthly_limit=150.0, user_id=uid))
        assert len(operations.get_all_budgets(uid)) == 2

    def test_get_budget_nonexistent_returns_none(self, test_user):
        assert operations.get_budget_for_category(test_user.id, "Nonexistent") is None

    def test_delete_budget_removes_record(self, test_user):
        uid = test_user.id
        operations.upsert_budget(Budget(category="Entertainment",
                                        monthly_limit=80.0, user_id=uid))
        assert operations.delete_budget(uid, "Entertainment") is True
        assert operations.get_budget_for_category(uid, "Entertainment") is None

    def test_delete_budget_nonexistent_returns_false(self, test_user):
        assert operations.delete_budget(test_user.id, "DoesNotExist") is False

    def test_budgets_scoped_per_user(self, test_user):
        """Two different users should have independent budgets."""
        user2 = operations.create_user("other_user", "pass999")
        operations.upsert_budget(Budget(category="Food & Dining",
                                        monthly_limit=500.0, user_id=test_user.id))
        assert operations.get_all_budgets(user2.id) == []


class TestExportToCsv:
    def test_csv_file_created(self, tmp_path, test_user):
        uid = test_user.id
        operations.add_expense(
            Expense(amount=10.0, category="Other", description="Test",
                    date="2024-01-01", user_id=uid)
        )
        filepath = str(tmp_path / "export.csv")
        count = operations.export_to_csv(uid, filepath)
        assert count == 1 and os.path.isfile(filepath)

    def test_csv_has_correct_headers(self, tmp_path, test_user):
        filepath = str(tmp_path / "empty.csv")
        operations.export_to_csv(test_user.id, filepath)
        with open(filepath) as f:
            header = f.readline().strip()
        assert all(col in header for col in ["ID", "Date", "Category", "Amount"])
