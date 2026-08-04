from fallback.retry import RetryExecutor


count = 0


def fake_provider():
    global count

    count += 1

    if count < 3:
        raise Exception("Temporary failure")

    return "Success!"


retry = RetryExecutor()

result = retry.run(fake_provider)

print(result)