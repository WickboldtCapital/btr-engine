from jinja2 import Template, Environment, meta

def render_dynamic_document(raw_markdown, calc_dict):
    """
    Takes raw markdown with {{ variables }} and injects the live calc dictionary.
    Includes custom formatting filters for currency and percentages.
    """
    # 1. Define custom formatting filters for the documents
    def format_currency(value):
        try:
            return f"${value:,.0f}"
        except (ValueError, TypeError):
            return value

    def format_percent(value):
        try:
            return f"{value * 100:.2f}%"
        except (ValueError, TypeError):
            return value
            
    def format_multiple(value):
        try:
            return f"{value:.2f}x"
        except (ValueError, TypeError):
            return value

    # 2. Set up the Jinja2 environment and add the filters
    env = Environment()
    env.filters['currency'] = format_currency
    env.filters['percent'] = format_percent
    env.filters['multiple'] = format_multiple

    try:
        # 3. Compile the template and render it with the calc data
        template = env.from_string(raw_markdown)
        rendered_text = template.render(**calc_dict)
        return rendered_text
    except Exception as e:
        return f"**Render Error:** {e}\n\nCheck your variable tags."

def get_available_variables(calc_dict):
    """Returns a sorted list of all available keys to display in the UI ledger."""
    return sorted(list(calc_dict.keys()))
