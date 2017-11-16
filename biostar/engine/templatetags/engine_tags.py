from textwrap import dedent

from django import forms
from django import template
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.forms import widgets
from django.utils.safestring import mark_safe

from biostar.engine import const
from biostar.engine.models import Project, Job, make_html

register = template.Library()

JOB_COLORS = {
    Job.ZOMBIE: "orange", Job.SPOOLED: "pink",
    Job.ERROR: "red", Job.QUEUED: "blue", Job.RUNNING: "teal", Job.COMPLETED: "green"
}


@register.simple_tag
def generate_form(json_text, **kwargs):
    return


@register.simple_tag
def sticky_label(obj):
    label = mark_safe('<span class ="ui label">Sticky</span>')
    return label if obj.sticky else ''

@register.simple_tag
def privacy_label(project):
    label = mark_safe(f'<span class ="ui label">{project.get_privacy_display()}</span>' )
    return label

@register.simple_tag
def job_color(job):
    """
    Returns a color based on job status.
    """
    return JOB_COLORS.get(job.state, "")


@register.simple_tag
def img(obj):
    """
    Returns the image associated with the object or a placeholder
    """
    if obj.image:
        return obj.image.url
    else:
        return static("images/placeholder.png")


@register.filter
def can_edit(user, instance):
    """Returns true is instance is editable by user."""

    if user.is_superuser or instance.owner == user:
        return True

    return False

@register.filter
def can_create(user):
    """Returns true if user may create a new object"""

    return user.is_authenticated()

@register.inclusion_tag('widgets/job_elapsed.html')
def job_minutes(job):
    """
    Returns a label for data sizes.
    """
    return dict(job=job)

@register.inclusion_tag('widgets/size_label.html')
def size_label(data):
    """
    Returns a label for data sizes.
    """
    return dict(data=data)


@register.inclusion_tag('widgets/type_label.html')
def type_label(data):
    """
    Returns a label for a data type.
    """
    color = "" if data.data_type == const.GENERIC_TYPE else "green"
    label = const.DATA_TYPES.get(data.data_type, "Generic")
    return dict(label=label, color=color)


@register.inclusion_tag('widgets/form_nonfield_errors.html')
def form_nonfield_errors(form):
    """
    Turns the error lists into a dictionary that can be iterated over.
    """
    errorlist = list(form.non_field_errors())
    context = dict(errorlist=errorlist)
    return context


@register.simple_tag
def field_state(field):
    """
    Returns the error label for a field.
    """
    if field.errors:
        return 'error'
    else:
        return ''


@register.filter
def markdown(text):
    """
    Generates HTML from a markdown value.
    """
    if not text:
        return ''
    text = dedent(text)
    html = make_html(text)
    return mark_safe(html)


@register.inclusion_tag('widgets/breadcrumb.html')
def breadcrumb(steps):
    """
    Generates the breadcrumb for a page.
    """
    return dict(steps=steps)




@register.inclusion_tag('widgets/menubar.html', takes_context=True)
def menubar(context, project=None, edit_project=False, create_project=False,
            data=None, edit_data=False, upload_data=False,
            analysis=None, edit_analysis=False
            ):
    user = context.request.user

    return dict(
        user=user,
        project=project, edit_project=edit_project, create_project=create_project,
        data=data, edit_data=edit_data, upload_data=upload_data,
        analysis=analysis, edit_analysis=edit_analysis,
    )


@register.filter(name='is_checkbox')
def is_checkbox(field):
    """
    Returns True if a field is a checkbox.
    """
    cond = isinstance(field, forms.BooleanField)
    return cond


@register.filter(name='is_selection')
def is_selection(field):
    """
    Returns True if a field's widget is a Selection
    """
    cond = isinstance(field.widget, widgets.Select)
    return cond
