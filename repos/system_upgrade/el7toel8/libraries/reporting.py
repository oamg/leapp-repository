from leapp.reporting import report


"""
Detail requirements:
    summary : str

Example:
    {'summary': 'Some text here'}
"""
RenderGeneric = {
    'html': '<h2 class="report-title">{{ title }}</h2><p class="report-summary">{{ summary }}</p>',
    'plaintext': '{{ title }}\n{{ summary }}'
}


"""
Detail requirements:
    summary : str
    remediation : str

Example:
    {'summary': 'Here is a summary', 'remediation': 'and --here-is -a solution'}
"""
RenderWithRemediation = {
    'html': ('<h2 class="report-title">{{ title }}</h2>'
             '<p class="report-summary">{{ summary }}</p>'
             '<h3>Remediation:</h3>'
             '<pre class="report-code">{{ remediation }}</pre>'),
    'plaintext': '{{ title }}\n{{ summary }}\nRemediation:\n{{ remediation }}'
}


"""
Detail requirements:
    summary : str
    links : List[{href:str, title:str}]

Example:
    {'summary': 'Summary with links',
     'links': [{'href': 'https://some.important.link.com', 'title': 'Knowledge base article'}]}
"""
RenderWithLinks = {
    'html': RenderGeneric['html'] +  # noqa: E131,W504
             ('<ul class="report-list">{% for link in links %}'
              '<li class="report-list-item">'
              ' <a href="{{ link.href }}" target="_blank" class="report-link">{{ link.title }}</a>'
              '</li>'
              '{% endfor %}</ul>'),

    'plaintext': ('{{ title }}\n'
                  '{{ summary }}\n'
                  'Links:\n'
                  '{% for link in links %}{{ link.title }} - {{ link.href }}{% endfor %}')
}


def _validate_args(title, summary):
    if not title:
        raise ValueError('Title not provided in the report.')
    if not summary:
        raise ValueError('Summary not provided in the report.')


def report_with_links(title=None, summary=None, links=None, **kwargs):
    """
    Produces a generic report with a list of links

    Where:
        links : List[{href:str, title:str}]
    """
    if not isinstance(links, list):
        raise ValueError('Links needs to be a list.')
    if not all([(isinstance(link, dict) and 'title' in link and 'href' in link) for link in links]):
        raise ValueError('links items need to be dictionaries with href and title keys.')
    _validate_args(title, summary)
    report(title=title, detail={'summary': summary, 'links': links}, renderers=RenderWithLinks, **kwargs)


def report_with_remediation(title=None, summary=None, remediation=None, **kwargs):
    """
    Produces a generic report with a remediation

    Where:
        remediation : str
    """
    _validate_args(title, summary)
    report(title=title, detail={'summary': summary, 'remediation': remediation},
           renderers=RenderWithRemediation, **kwargs)


def report_generic(title=None, summary=None, **kwargs):
    """
    Produces a generic report with a summary
    """
    _validate_args(title, summary)
    report(title=title, detail={'summary': summary}, renderers=RenderGeneric, **kwargs)
