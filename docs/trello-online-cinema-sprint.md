# Online Cinema: Trello Sprint Plan

Sprint dates: 2026-07-03 - 2026-07-05

Recommended board name: `Online Cinema - 3 Day Sprint`

## Board Lists

- `Backlog`
- `To Do`
- `In Progress`
- `Code Review`
- `Testing`
- `Done`
- `Blocked`

## Labels

- `P0 Critical` - red
- `P1 High` - orange
- `P2 Medium` - yellow
- `Setup/DevOps` - purple
- `Auth` - blue
- `Movies` - green
- `Cart/Orders` - lime
- `Payments` - pink
- `Docs` - sky
- `Tests` - black
- `Stretch` - gray

## Team Placeholders

Replace placeholders with real Trello members:

- `You` - project setup, Docker, Poetry, CI, README, repo rules
- `Dev A` - authorization and users
- `Dev B` - movies catalog and moderation
- `Dev C` - cart and orders
- `Dev D` - payments, webhooks, notifications
- `All` - code review, tests, integration fixes

## Working Rules

- One task = one branch.
- Branch format: `feature/<domain-short-name>`, `fix/<short-name>`, or `chore/<short-name>`.
- Every PR needs at least 2 approvals before merge.
- Every custom endpoint must have tests.
- Rebase feature branches on the latest main branch before final review if main changed.
- No direct commits to `main`.
- Swagger/OpenAPI docs must be updated with every endpoint card.

## Day 1 - 2026-07-03: Foundation

### Card 1: Project bootstrap, Docker, Poetry, README

Assignee: `You`

Due: 2026-07-03 13:00

Labels: `P0 Critical`, `Setup/DevOps`, `Docs`

Branch: `chore/project-bootstrap`

Description:
Prepare the base project so every developer can run the same environment from the first day.

Checklist:
- Initialize FastAPI project structure.
- Add Poetry config with pinned Python version and base dependencies.
- Add Dockerfile for the API service.
- Add docker-compose with API, PostgreSQL, Redis, Celery worker, Celery beat, and MinIO.
- Add `.env.example`.
- Add Makefile or documented commands for local development.
- Add initial README with setup, Docker run, tests, migrations, and common commands.
- Verify the app starts with one command.

Acceptance criteria:
- A new developer can clone the repo, copy `.env.example`, run one command, and open the API.
- All service versions are fixed or clearly defined.
- README is detailed enough for the team to start without extra explanation.

### Card 2: GitHub repository rules and PR workflow

Assignee: `You`

Due: 2026-07-03 16:00

Labels: `P0 Critical`, `Setup/DevOps`

Branch: `chore/github-workflow`

Description:
Configure teamwork rules for safe collaboration.

Checklist:
- Add PR template.
- Add issue/task template if useful.
- Add branch protection for `main`.
- Require at least 2 approvals before merge.
- Require CI checks before merge.
- Add labels matching Trello domains.
- Document branch naming and rebase workflow in README.

Acceptance criteria:
- PRs cannot be merged without required checks and reviews.
- Team has a clear workflow for branches, rebases, and reviews.

### Card 3: Base architecture, config, database, migrations

Assignee: `Dev A`

Due: 2026-07-03 18:00

Labels: `P0 Critical`, `Setup/DevOps`

Branch: `feature/base-architecture`

Description:
Create the technical base used by all feature teams.

Checklist:
- Add settings/config module.
- Add SQLAlchemy database connection/session.
- Add Alembic migrations.
- Add shared base model conventions.
- Add app router structure by domain.
- Add health check endpoint.
- Add basic exception response format.

Acceptance criteria:
- Developers can add models and migrations consistently.
- Health endpoint works locally and in Docker.

### Card 4: User, profile, roles models and migrations

Assignee: `Dev A`

Due: 2026-07-03 20:00

Labels: `P1 High`, `Auth`

Branch: `feature/auth-models`

Description:
Implement user-related database models.

Checklist:
- Add `UserGroupEnum` with USER, MODERATOR, ADMIN.
- Add `GenderEnum`.
- Add `UserGroup`, `User`, and `UserProfile` models.
- Add relationships and unique constraints.
- Add migration.
- Seed default user groups.

Acceptance criteria:
- User tables are created by migrations.
- Default groups exist after setup/seed command.

### Card 5: Movie domain models and migrations

Assignee: `Dev B`

Due: 2026-07-03 20:00

Labels: `P1 High`, `Movies`

Branch: `feature/movie-models`

Description:
Implement movie catalog database models.

Checklist:
- Add `Genre`, `Star`, `Director`, `Certification`, and `Movie`.
- Add many-to-many tables for genres, stars, and directors.
- Add unique constraint for movie identity: name, year, time.
- Add movie UUID field.
- Add migration.
- Add seed/sample data command or fixture.

Acceptance criteria:
- Movies and related entities can be inserted and queried.
- Constraints prevent duplicate movie records.

## Day 2 - 2026-07-04: Core Features

### Card 6: Registration, activation token, activation email

Assignee: `Dev A`

Due: 2026-07-04 11:00

Labels: `P0 Critical`, `Auth`

Branch: `feature/auth-registration-activation`

Description:
Allow users to register and activate accounts by email token.

Checklist:
- Add registration endpoint with email uniqueness validation.
- Hash passwords securely.
- Create inactive user by default.
- Create activation token valid for 24 hours.
- Send activation email.
- Add account activation endpoint.
- Add resend activation token endpoint.
- Add Celery beat task to delete expired activation tokens.
- Add tests for success and failure cases.

Acceptance criteria:
- User cannot log in before activation.
- Expired activation token cannot activate account.
- Resend creates a new valid token.

### Card 7: JWT login, refresh, logout

Assignee: `Dev A`

Due: 2026-07-04 14:00

Labels: `P0 Critical`, `Auth`

Branch: `feature/auth-jwt-session`

Description:
Implement JWT session flow.

Checklist:
- Add login endpoint.
- Return access and refresh tokens.
- Store refresh tokens in DB.
- Add refresh endpoint with short-lived access token.
- Add logout endpoint that deletes/revokes refresh token.
- Add auth dependency for protected routes.
- Add tests for login, refresh, logout, inactive user, invalid token.

Acceptance criteria:
- Logged-out refresh token cannot be reused.
- Protected endpoints reject missing or invalid access token.

### Card 8: Password management

Assignee: `Dev A`

Due: 2026-07-04 17:00

Labels: `P1 High`, `Auth`

Branch: `feature/auth-password-management`

Description:
Support password change and forgot-password reset flow.

Checklist:
- Add password complexity validation.
- Add change password endpoint requiring old password.
- Add forgot password endpoint.
- Add password reset token model and migration if not included yet.
- Send reset email for active registered users.
- Add reset password endpoint.
- Add token expiration validation.
- Add tests.

Acceptance criteria:
- Weak passwords are rejected.
- Password reset works without old password only with a valid reset token.

### Card 9: Movie CRUD for moderators

Assignee: `Dev B`

Due: 2026-07-04 14:00

Labels: `P1 High`, `Movies`

Branch: `feature/moderator-movie-crud`

Description:
Allow moderators/admins to manage movies and related catalog entities.

Checklist:
- Add CRUD endpoints for movies.
- Add CRUD endpoints for genres, actors/stars, directors, certifications.
- Restrict write endpoints to Moderator/Admin.
- Prevent deleting movie if it was purchased.
- Add tests for permissions and delete validation.
- Document endpoints in Swagger.

Acceptance criteria:
- Regular users cannot create/update/delete catalog data.
- Purchased movies cannot be deleted.

### Card 10: Public movie catalog, search, filters, sorting

Assignee: `Dev B`

Due: 2026-07-04 18:00

Labels: `P0 Critical`, `Movies`

Branch: `feature/movie-catalog`

Description:
Implement user-facing movie catalog browsing.

Checklist:
- Add paginated movie list endpoint.
- Add movie detail endpoint.
- Add filters by year, IMDb rating, genre, certification, price.
- Add sorting by price, release year, IMDb rating, popularity/votes.
- Add search by title, description, actor/star, director.
- Add genre list endpoint with movie count.
- Add tests for pagination, search, filters, and sorting.

Acceptance criteria:
- Users can find movies through list, detail, search, filter, and sort flows.
- Genre endpoint returns counts and can be used to open related movies.

### Card 11: Cart models and cart endpoints

Assignee: `Dev C`

Due: 2026-07-04 16:00

Labels: `P0 Critical`, `Cart/Orders`

Branch: `feature/cart`

Description:
Implement shopping cart behavior.

Checklist:
- Add `Cart` and `CartItem` models.
- Add migration.
- Auto-create cart for users when needed.
- Add endpoint to view cart.
- Add endpoint to add movie to cart.
- Add endpoint to remove item from cart.
- Add endpoint to clear cart.
- Prevent duplicate cart items.
- Prevent adding already purchased movies.
- Add tests.

Acceptance criteria:
- User has one cart.
- Same movie cannot be added twice.
- Purchased movies cannot be added again.

### Card 12: Order models and order lifecycle

Assignee: `Dev C`

Due: 2026-07-04 20:00

Labels: `P0 Critical`, `Cart/Orders`

Branch: `feature/orders`

Description:
Create orders from cart and manage order states.

Checklist:
- Add `OrderStatus` enum.
- Add `Order` and `OrderItem` models.
- Add migration.
- Add create order from cart endpoint.
- Validate cart is not empty.
- Exclude already purchased/unavailable movies.
- Store `price_at_order`.
- Revalidate total amount before payment.
- Add order list/detail endpoints for user.
- Add cancel pending order endpoint.
- Add admin order list with filters by user/date/status.
- Add tests.

Acceptance criteria:
- Order captures a stable snapshot of items and prices.
- Paid orders cannot be canceled through normal cancel endpoint.

## Day 3 - 2026-07-05: Payments, Docs, Tests, Integration

### Card 13: Stripe payment flow and webhooks

Assignee: `Dev D`

Due: 2026-07-05 12:00

Labels: `P0 Critical`, `Payments`

Branch: `feature/stripe-payments`

Description:
Implement Stripe payment session and webhook processing.

Checklist:
- Add `PaymentStatus` enum.
- Add `Payment` and `PaymentItem` models.
- Add migration.
- Add endpoint to create Stripe checkout/payment session for an order.
- Verify order total before payment.
- Add Stripe webhook endpoint.
- Update payment status from webhook.
- Update order status to paid after successful payment.
- Move movies to purchased list after successful payment.
- Add payment history endpoint for users.
- Add admin payment list with filters.
- Add tests with mocked Stripe/webhook events.

Acceptance criteria:
- Successful webhook marks order as paid and creates payment records.
- Invalid webhook signature is rejected.
- User can see payment history.

### Card 14: Purchased movies access and duplicate purchase protection

Assignee: `Dev C`

Due: 2026-07-05 14:00

Labels: `P1 High`, `Cart/Orders`, `Payments`

Branch: `feature/purchased-movies`

Description:
Track purchased movies and use this data across cart, orders, and movie deletion validation.

Checklist:
- Add purchased movie relation/model if needed.
- Add endpoint for user purchased movies.
- Prevent already purchased movies from cart/order.
- Make movie delete validation check purchases.
- Add tests.

Acceptance criteria:
- Users cannot buy the same movie twice.
- Purchased movie data is available for user profile/library flow.

### Card 15: Favorites, likes/dislikes, ratings, comments

Assignee: `Dev B`

Due: 2026-07-05 16:00

Labels: `P2 Medium`, `Movies`

Branch: `feature/movie-social-actions`

Description:
Add user interactions with movies.

Checklist:
- Add favorite movie model/endpoints.
- Add likes/dislikes model/endpoints.
- Add 10-point rating model/endpoints.
- Add comments model/endpoints.
- Add replies to comments.
- Add notification trigger for comment replies or likes.
- Add tests.

Acceptance criteria:
- Users can manage favorites and use catalog functions on favorites.
- Rating is restricted to 1-10.
- Comment reply/like can trigger notification.

### Card 16: Notifications service

Assignee: `Dev D`

Due: 2026-07-05 16:00

Labels: `P2 Medium`, `Movies`, `Payments`

Branch: `feature/notifications`

Description:
Send required user notifications.

Checklist:
- Add email sending abstraction.
- Send activation email.
- Send password reset email.
- Send payment confirmation email.
- Notify users about comment replies/likes.
- Add tests with mocked mail backend.

Acceptance criteria:
- Notification side effects are testable and do not block endpoint tests.

### Card 17: Swagger/OpenAPI documentation and access restriction

Assignee: `You`

Due: 2026-07-05 17:00

Labels: `P1 High`, `Docs`, `Auth`

Branch: `feature/swagger-docs-access`

Description:
Make API documentation complete and restrict access to authorized users.

Checklist:
- Add endpoint descriptions and request/response schemas.
- Document custom actions and query parameters.
- Add examples for auth, movie filters, cart, orders, and payments.
- Restrict Swagger UI/OpenAPI access to authorized users.
- Add README section about API docs.

Acceptance criteria:
- Swagger clearly explains how to use every custom endpoint.
- Unauthenticated users cannot access private API docs if this is required by project rules.

### Card 18: CI pipeline with linting, typing, tests, coverage

Assignee: `You`

Due: 2026-07-05 18:00

Labels: `P0 Critical`, `Setup/DevOps`, `Tests`

Branch: `chore/ci-tests-coverage`

Description:
Add automated checks required for protected PRs.

Checklist:
- Add GitHub Actions workflow.
- Run formatting/linting check.
- Run type check with mypy if configured.
- Run pytest.
- Generate coverage report.
- Cache Poetry dependencies if useful.
- Document local equivalents in README.

Acceptance criteria:
- CI fails on test or lint failure.
- Branch protection can require this workflow before merge.

### Card 19: Integration tests for main user flow

Assignee: `All`

Due: 2026-07-05 19:00

Labels: `P0 Critical`, `Tests`

Branch: `test/main-user-flow`

Description:
Cover the main end-to-end path through the application.

Checklist:
- Register user.
- Activate account.
- Login and refresh token.
- Browse/search/filter movies.
- Add movie to cart.
- Create order.
- Pay order with mocked Stripe webhook.
- Verify purchased movie.
- Verify duplicate purchase is blocked.

Acceptance criteria:
- Main business flow has automated coverage.
- Tests can be run locally and in CI.

### Card 20: Final integration QA, bugfix, demo readiness

Assignee: `All`

Due: 2026-07-05 21:00

Labels: `P0 Critical`, `Tests`, `Docs`

Branch: `fix/final-integration`

Description:
Stabilize the project before final submission/demo.

Checklist:
- Pull latest `main`.
- Rebase active branches if needed.
- Run Docker compose from a clean clone/setup.
- Run migrations from scratch.
- Run all tests.
- Check Swagger manually.
- Verify README setup instructions.
- Fix integration bugs.
- Prepare short demo script.

Acceptance criteria:
- Project starts from clean setup.
- Main user flow works.
- README, tests, and Swagger are ready for review.

## Stretch Cards

### Card 21: AWS EC2 deployment

Assignee: `You` or `Dev D`

Due: 2026-07-05 21:00

Labels: `P2 Medium`, `Setup/DevOps`, `Stretch`

Branch: `chore/aws-ec2-deploy`

Description:
Deploy the app to AWS EC2 after CI passes and PRs are merged.

Checklist:
- Prepare production Docker compose or deployment script.
- Configure environment variables/secrets.
- Configure GitHub Actions deploy job.
- Verify deployed health endpoint.
- Document deployment steps.

Acceptance criteria:
- App can be deployed automatically or with documented manual steps.

### Card 22: Refund flow

Assignee: `Dev D`

Due: 2026-07-05 21:00

Labels: `P2 Medium`, `Payments`, `Stretch`

Branch: `feature/refunds`

Description:
Support refund request/admin processing if time allows.

Checklist:
- Add refund request endpoint.
- Add admin approval/reject endpoint.
- Update payment status to refunded.
- Add tests.

Acceptance criteria:
- Paid orders are not canceled directly; refund flow handles them separately.

## Suggested Initial Trello Setup

Create the following cards first in `To Do`:

1. Project bootstrap, Docker, Poetry, README
2. GitHub repository rules and PR workflow
3. Base architecture, config, database, migrations
4. User, profile, roles models and migrations
5. Movie domain models and migrations

After Card 1 and Card 3 are merged, unblock the feature cards for Auth, Movies, Cart, Orders, and Payments.

