from datetime import datetime, timezone
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.utils.http import url_has_allowed_host_and_scheme
from django.shortcuts import redirect, render, get_object_or_404
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from .models import Assignment, Submission, Group
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

@login_required
def index(request):
    # fetch all assignments and send them into the template
    assignments = Assignment.objects.all()
    return render(request, 'index.html', {'assignments': assignments})

@login_required
def assignment(request, assignment_id):
    # fetch this specific assignment
    assignment = get_object_or_404(Assignment, id=assignment_id)

    # determine the user type
    is_student = request.user.groups.filter(name="Students").exists()
    is_ta = request.user.groups.filter(name="Teaching Assistants").exists()
    is_superuser = request.user.is_superuser

    # setup data for student submissions of this assignment
    student_submission = None
    submission_status = ""

    # determine if this is past due
    now = datetime.now(timezone.utc)
    past_due = now.date() > assignment.deadline.date()

    if is_student:
        # fetch this student's submission
        student_submission = assignment.submission_set.filter(author=request.user).first()

        # if the fetch was successful...
        if student_submission:

            # check for the file
            if student_submission.file:
                filename = student_submission.file.name
            else:
                filename = "No File"

            # check for the score
            if student_submission.score is not None:
                submission_status = f"Your submission, {filename}, received {int(student_submission.score)}/{assignment.points} points ({(student_submission.score / assignment.points) * 100:.2f}%)."

            # check if no score and past due
            elif past_due:
                submission_status = f"Your submission, {filename}, is being graded."

            # no score but not due yet
            else:
                submission_status = f"Your current submission is {filename}."

        # if the fetch was not successful (no submission but student exists)
        else:

            # check if the student is out of luck
            if past_due:
                submission_status = "You did not submit this assignment and received 0 points."

            # no submission but not due yet
            else:
                submission_status = "No current submission."

    # submitting a submission
    if request.method == "POST":
        # fetch the uploaded file
        submission_file = request.FILES.get('submission_file')

        # if file couldn't be fetched, just redirect to the assignment page
        if not submission_file:
            return redirect(f'/{assignment_id}/')

        # if deadline has passed, don't allow this submission (out of luck)
        if past_due:
            return HttpResponseBadRequest("The deadline has passed. You cannot submit this assignment.")

        # make sure someone isn't uploading a huge file
        if submission_file.size > 64 * 1024 * 1024:
            error_message = "File size must be under 64 MiB."

            # show error message
            return render(request, 'assignment.html', {
                'assignment': assignment,
                'student_submission': student_submission,
                'submission_status': submission_status,
                'error_message': error_message,
            })

        # make sure this is a pdf file
        if not is_pdf(submission_file):
            error_message = "Only valid PDF files are allowed."

            # show error message
            return render(request, 'assignment.html', {
                'assignment': assignment,
                'student_submission': student_submission,
                'submission_status': submission_status,
                'error_message': error_message,
            })

        # if submission exists, update it; if not, create a new one and call pick_grader
        if student_submission:
            student_submission.file = submission_file
        else:
            assigned_grader = pick_grader()
            if not assigned_grader:
                return HttpResponse("No TA available to grade this submission.")

            student_submission = Submission(
                assignment=assignment,
                author=request.user,
                grader=assigned_grader,
                file=submission_file,
                score=None
            )

        # save the changes/additions
        student_submission.save()

        # redirect to the assignment page with the new changes/additions
        return redirect(f'/{assignment_id}/')

    # compile the stats for the TA's (or admin)
    total_submissions = assignment.submission_set.count()
    submissions_assigned_to_you = assignment.submission_set.filter(grader__username=request.user.username).count()
    total_students = Group.objects.get(name="Students").user_set.count()

    # send ALL this data into the template
    return render(request, 'assignment.html', {
        'assignment': assignment,
        'student_submission': student_submission,
        'submission_status' : submission_status,
        'total_submissions': total_submissions,
        'submissions_assigned_to_you': submissions_assigned_to_you,
        'total_students': total_students,
        'is_student': is_student,
        'is_ta': is_ta,
        'is_superuser': is_superuser,
        'past_due': past_due,
    })

@login_required
def submissions(request, assignment_id):

    # determine what type of user
    is_ta = request.user.groups.filter(name="Teaching Assistants").exists()
    is_superuser = request.user.is_superuser

    # make sure only TA's and Admins can see submissions
    if not is_ta or is_superuser:
        raise PermissionDenied("You do not have permission to access this page.")

    # make sure assignment actually exists
    try:
        assignment = Assignment.objects.get(id=assignment_id)
    except Assignment.DoesNotExist:
        raise Http404("Assignment not found")

    # determine what submissions to pass into the template
    if is_ta:
        submissions = Submission.objects.filter(assignment=assignment, grader=request.user)
    elif is_superuser:
        submissions = Submission.objects.filter(assignment=assignment)
    else:
        submissions = Submission.objects.none()

    # store potential errors below in here
    errors = {}
    general_errors = []

    # submission updates
    if request.method == "POST":
        submissions_to_update = []

        # loop through all the changes (TA could enter numerous scores at once)
        for key, value in request.POST.items():
            if key.startswith('grade-'):
                try:
                    submission_id = int(key.removeprefix('grade-'))

                    # Ensure the submission exists for the correct assignment
                    submission = Submission.objects.get(id=submission_id, assignment=assignment)

                    if value.strip() == '':
                        # set grade to None
                        submission.change_grade(request.user, None)
                    else:
                        # set grade to the entered value
                        score = float(value)

                        # also check for valid score bounds
                        if score < 0 or score > assignment.points:
                            raise ValueError(f"Grade must be between 0 and {assignment.points}.")

                        # now update it
                        submission.change_grade(request.user, score)

                    submissions_to_update.append(submission)

                # possible errors
                except ValueError:
                    errors.setdefault(submission_id, []).append("Invalid value type. Only enter valid numbers.")
                except Submission.DoesNotExist:
                    general_errors.append(f"Invalid submission ID: {submission_id}")

        # if there are no errors, save valid submissions and redirect
        if not errors and not general_errors:
            if submissions_to_update:
                Submission.objects.bulk_update(submissions_to_update, ['score'])

            # redirect to avoid duplicate form submissions on page reload
            return redirect(f'/{assignment_id}/submissions')

        # render page with errors if this point is reached
        return render(request, 'submissions.html', {
            'assignment': assignment,
            'submissions': submissions,
            'errors': errors,
            'general_errors': general_errors,
        })

    # render for GET requests
    return render(request, 'submissions.html', {
        'assignment': assignment,
        'submissions': submissions,
        'errors': errors,  # Ensure errors are passed even on GET request
    })
    

@login_required
def profile(request):

    # the logged-in user
    user = request.user
    user_type = None

    # setup context data
    assignments = Assignment.objects.order_by("deadline")
    assignment_details = []
    current_grade = 'N/A'

    # admins
    if user.is_superuser:
        user_type = "Admin"

        # grab the instructed data
        for assignment in assignments:
            total_submissions = assignment.submission_set.count()
            graded_submissions = assignment.submission_set.filter(score__isnull=False).count()

            assignment_details.append({
                'assignment': assignment,
                'total_submissions': total_submissions,
                'graded_submissions': graded_submissions,
            })

    # TA's
    elif user.groups.filter(name="Teaching Assistants").exists():
        user_type = "TA"

        # grab the instructed data
        for assignment in assignments:
            assigned_submissions = assignment.submission_set.filter(grader=user)
            total_submissions = assigned_submissions.count()
            graded_submissions = assigned_submissions.filter(score__isnull=False).count()

            assignment_details.append({
                'assignment': assignment,
                'total_submissions': total_submissions,
                'graded_submissions': graded_submissions,
            })

    # students
    else:
        user_type = "Student"

        # used for calculating overall grade
        total_available_points = 0.0
        total_earned_points = 0.0

        # grab the instructed data
        for assignment in assignments:

            # attempt to fetch the submission
            submission = assignment.submission_set.filter(author=user).first()
            assignment_status = 'Not submitted'

            # submission is there
            if submission:

                if submission.score is not None:
                    # submission is graded
                    assignment_status = f'{submission.score / assignment.points * 100}%'
                    available_points = assignment.weight
                    earned_points = (submission.score / assignment.points) * assignment.weight

                    total_available_points += available_points
                    total_earned_points += earned_points
                else:
                    # submission is not graded yet
                    assignment_status = 'Pending'
                    available_points = 0
                    earned_points = 0

            # submission is not there; deadline has not passed
            elif datetime.now(timezone.utc).date() <= assignment.deadline.date():
                # Not submitted but not due yet
                assignment_status = 'Not due'
                available_points = 0
                earned_points = 0

            # submission is not there; deadline HAS passed (out of luck)
            else:
                # Past due and no submission (missing)
                assignment_status = 'Missing'
                available_points = assignment.weight
                earned_points = 0

                total_available_points += available_points

            assignment_details.append({
                'assignment': assignment,
                'submission_status': assignment_status,
                'available_points': available_points,
                'earned_points': earned_points,
            })

        # determine the overall grade
        if total_available_points > 0:
            # i chose to round to 2 decimal places
            current_grade = round((total_earned_points / total_available_points) * 100, 2)
        else:
            current_grade = 100

    # render this data; for the correct user type as well
    return render(request, 'profile.html', {
        'assignment_details': assignment_details,
        'user': request.user,
        'current_grade': current_grade,
        'user_type': user_type,
    })

def logout_form(request):
    logout(request)
    return redirect('/profile/login/')

def login_form(request):
    # fetch the next value so we can redirect the user to the url they were initially trying to access
    next_url = request.GET.get("next", "/profile/") # default to profile if they were simply going to the login url

    # on log in submit
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        next_url = request.POST.get("next", "/profile/")

        # make sure credentials are correct
        user = authenticate(request, username=username, password=password)

        # if successful
        if user is not None:
            login(request, user)
            # check for valid next urls
            if url_has_allowed_host_and_scheme(next_url, None):
                return redirect(next_url)
            else:
                return redirect("/")

        # if not successful
        else:
            # render error message and have user try again
            return render(request, "login.html", {
                "error": "Invalid username or password.",
                "next": next_url
            })

    # initial GET render
    return render(request, "login.html", {"next": next_url})

@login_required
def show_upload(request, filename):
    try:
        # access the submission for this file name
        submission = Submission.objects.get(file=filename)
        submission.view_submission(request.user)

        # make sure this is a pdf
        if not is_pdf(submission.file):
            raise Http404("Invalid file format.")

        # open it up (download it)
        response = HttpResponse(submission.file.open(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{submission.file.name}"'
        return response

    except(Submission.DoesNotExist, PermissionDenied):
        raise Http404("File not found or access denied.")


# HELPER FUNCTIONS

def is_pdf(submission_file):
    if not submission_file.name.lower().endswith('.pdf') or not next(submission_file.chunks()).startswith(b'%PDF-'):
        return False
    else:
        return True

def pick_grader():
    # fetch all the TA's
    ta_group = Group.objects.get(name="Teaching Assistants")

    # sort them by how many total assignments they have to grade
    ta_counts = ta_group.user_set.annotate(
        total_assigned=Count('graded_set')
    ).order_by('total_assigned')

    # assign to whoever has the least
    if ta_counts.exists():
        return ta_counts.first()
    else:
        return None