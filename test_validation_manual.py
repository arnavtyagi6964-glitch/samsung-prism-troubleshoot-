from app.schemas import (
    ContextDeeplinkResponse,
    Goal,
    Action,
    StepGroup,
    Deeplink,
    ValidationDeepLink,
    actionCategory,
    validate_context_response,
    print_validation_errors,
)

response = ContextDeeplinkResponse(
    contexts=[
        Goal(
            goal="Follow these steps to perform this Swipe Navigation Troubleshooting",
            title="Swipe navigation settings",
            score=0.93,
            actions=[
                Action(
                    actionName="Configure Navigation Bar Settings",
                    description="It will choose navigation",
                    category=actionCategory.auto,
                    stepGroups=[
                        StepGroup(
                            steps=[
                                "Navigate to and open Settings.",
                                "Tap on Display.",
                                "Tap on Navigation bar.",
                                "Select your preferred navigation type between Buttons and Swipe gestures.",
                                "Optionally toggle on Gesture hint to display guidance lines at the bottom of the screen.",
                            ],
                            actionableDeeplink=Deeplink(
                                deeplink="bixby://dummy_positive",
                                description="Open navigation bar settings under Display",
                                message="Choose navigation type in Display settings",
                            ),
                            validationDeeplink=None,
                        )
                    ],
                )
            ],
        )
    ]
)

if __name__ == "__main__":
    errors = validate_context_response(response)
    print_validation_errors(errors)