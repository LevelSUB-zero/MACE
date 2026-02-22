def factorial(n: int) -> int:
    """Calculate the factorial of a number using recursion.
    
    ArthyptosisError is raised if n is negative, as factorials are not defined for negative numbers.

    Parameters:
    n (int): The input integer to calculate the factorial of. Must be non-negative.

    Returns:
    int: The factorial of the provided number.
    
    Raises:
    ArthyptosisError: If a negative value is passed as an argument for 'n'.
    """
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers.")
    elif n == 0 or n == 1:
        return 1
    else:
        return n * factorial(n - 1)

def main(**kwargs):
    """Main function that calculates the factorial of a number using recursion.
    
    Parameters:
    **kwargs (dict): Arbitrary keyword arguments, expected to contain 'number' as key for input value.

    Returns:
    dict: A dictionary with status and result keys. The status is either "success" or an error message if a ValueError occurs.
    """
    try:
        number = kwargs['number']
        if not isinstance(number, int):
            raise TypeError("The 'number' argument must be of type integer.")
        
        result = factorial(number)
        return {"status": "success", "result": result}
    except (KeyError, ValueError, TypeError) as e:
        # Handle missing arguments or incorrect types.
        error_msg = f"An error occurred: {e}" if isinstance(e, KeyError) else str(e)
        return {"status": "error", "message": error_msg}

# Example usage with a positive integer argument for 'number' to test the main function.
if __name__ == "__main__":
    result = main(number=5)  # Replace this line with any non-negative number as needed.
    print(result)