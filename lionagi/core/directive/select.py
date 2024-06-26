async def select(
    sentence,
    choices=None,
    instruction=None,
    confidence_score=False,
    reason=False,
    retries=2,
    delay=0.5,
    backoff_factor=2,
    default_value=None,
    timeout=None,
    branch_name=None,
    system=None,
    messages=None,
    service=None,
    sender=None,
    llmconfig=None,
    tools=None,
    datalogger=None,
    persist_path=None,
    tool_manager=None,
    **kwargs,
):
    """
    Selects an item from given choices based on a given context using a language model.

    Args:
        sentence (str | list | dict): The given context.
        choices (Optional[list]): The list of choices to select from.
        instruction (Optional[str]): The instruction for selection.
        confidence_score (bool): Whether to include the confidence score in the output (default: False).
        reason (bool): Whether to include the reason for the selection in the output (default: False).
        retries (int): The number of retries for the API call (default: 2).
        delay (float): The initial delay between retries in seconds (default: 0.5).
        backoff_factor (float): The backoff factor for exponential delay between retries (default: 2).
        default_value (Optional[Any]): The default value to return if the API call fails (default: None).
        timeout (Optional[float]): The timeout for the API call in seconds (default: None).
        branch_name (Optional[str]): The name of the branch to use for selection.
        system (Optional[Any]): The system configuration for the branch.
        messages (Optional[Any]): The messages to initialize the branch with.
        service (Optional[Any]): The service to use for selection.
        sender (Optional[str]): The sender of the selection request.
        llmconfig (Optional[Any]): The configuration for the language model.
        tools (Optional[Any]): The tools to use for selection.
        datalogger (Optional[Any]): The data logger for the branch.
        persist_path (Optional[str]): The path to persist the branch data.
        tool_manager (Optional[Any]): The tool manager for the branch.
        **kwargs: Additional keyword arguments for the API call.

    Returns:
        SelectTemplate: The select template with the selected item.
    """
    branch = Branch(
        name=branch_name,
        system=system,
        messages=messages,
        service=service,
        sender=sender,
        llmconfig=llmconfig,
        tools=tools,
        datalogger=datalogger,
        persist_path=persist_path,
        tool_manager=tool_manager,
    )

    _template = SelectTemplate(
        sentence=sentence,
        choices=choices,
        instruction=instruction,
        confidence_score=confidence_score,
        reason=reason,
    )

    await func_call.rcall(
        branch.chat,
        form=_template,
        retries=retries,
        delay=delay,
        backoff_factor=backoff_factor,
        default=default_value,
        timeout=timeout,
        **kwargs,
    )

    ans = _template.answer

    if ans not in _template.choices:
        _template.answer = StringMatch.choose_most_similar(ans, _template.choices)

    return _template
