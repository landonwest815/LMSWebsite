from django.core.exceptions import PermissionDenied
from django.db import models
from django.contrib.auth.models import User, Group

class Assignment(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    deadline = models.DateTimeField()
    weight = models.IntegerField()
    points = models.IntegerField()

class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='authored_submissions')
    grader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='graded_set')
    file = models.FileField(upload_to='')
    score = models.FloatField(null=True, blank=True)

    def change_grade(self, user, updated_grade):
        # make sure the user is the grader and not the student (or anyone else)
        if user != self.grader:
            raise PermissionDenied("You do not have permission to change this grade.")

        # simply update the score
        self.score = updated_grade

    def view_submission(self, user):
        # ensure the user has permission to view the submission
        if user != self.author and user != self.grader and not user.is_superuser:
            raise PermissionDenied("You do not have permission to view this submission.")

        # send back the file
        return self.file
