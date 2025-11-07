from django.db import models

class GeneratedReport(models.Model):
    report_type = models.CharField(max_length=50)
    referentiel = models.CharField(max_length=50, blank=True, null=True)
    start_period = models.DateField()
    end_period = models.DateField()
    file_pdf = models.FileField(upload_to='reports/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.report_type} ({self.start_period} - {self.end_period})"

