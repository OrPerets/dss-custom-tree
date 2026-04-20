class EmployeeTreeValidationError(Exception):
    def __init__(self, issues):
        self.issues = issues
        message = issues[0]["message"] if issues else "Employee tree validation failed."
        super(EmployeeTreeValidationError, self).__init__(message)

    def to_dict(self):
        return {
            "error": "employee_tree_validation_error",
            "message": str(self),
            "issues": self.issues,
        }
