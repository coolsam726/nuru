"""example_app.resources — all resource classes."""
from .author_resource import AuthorResource
from .subject_resource import SubjectResource
from .book_resource import BookResource
from .member_resource import MemberResource
from .checkout_resource import CheckoutResource
from .staff_user_resource import StaffUserResource
from .role_resource import RoleResource

__all__ = [
    "AuthorResource", "SubjectResource", "BookResource",
    "MemberResource", "CheckoutResource", "StaffUserResource", "RoleResource",
]

