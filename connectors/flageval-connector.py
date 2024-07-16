import logging, json

import aiohttp
from aiohttp import ClientResponse
from typing import Callable
from moonshot.src.connectors.connector import Connector, perform_retry
from moonshot.src.connectors.connector_prompt_arguments import ConnectorPromptArguments
from moonshot.src.connectors_endpoints.connector_endpoint_arguments import (
    ConnectorEndpointArguments,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FlagJudgeConnector(Connector):
    def __init__(self, ep_arguments: ConnectorEndpointArguments):
        # Initialize super class
        super().__init__(ep_arguments)

    @Connector.rate_limited
    @perform_retry
    async def get_response(self, prompt: str, prediction: str, ground_truth: str) -> str:
        """
        Retrieve and return a response.
        This method is used to retrieve a response, typically from an object or service represented by
        the current instance.

        Returns:
            str: retrieved response data
        """
        # Merge self.optional_params with additional parameters
        new_params = {
            "model": "flageval_judgemodel",
            "prompt": prompt,
            "pred": prediction,
            "gold": ground_truth,
            "echo": False,
            "stream": False
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.endpoint,
                headers=self._prepare_headers(),
                json=new_params,
            ) as response:
                return await self._process_response(response)

    @Connector.rate_limited
    @perform_retry
    async def get_prediction(
        self,
        generated_prompt: ConnectorPromptArguments
    ):
        """
        The method then returns the `judge_result` generated by flagjudge model.

        Args:
            generated_prompt (ConnectorPromptArguments): The prompt to be predicted.

        Returns:
            judge_result: The `judge_result` generated by flagjudge model.

        Raises:
            Exception: If there is an error during prediction.
        """
        try:
            print(f"Predicting prompt {generated_prompt.prompt_index} [{self.id}]")

            judge_result = await self.get_response(
                generated_prompt.prompt,
                generated_prompt.predicted_results,
                generated_prompt.target
            )
            # Return the judge_result
            return judge_result

        except Exception as e:
            print(f"Failed to get prediction: {str(e)}")
            raise e


    def _prepare_headers(self) -> dict:
        """
        Prepare HTTP headers for authentication using a bearer token.

        This function takes a bearer token as input and prepares a dictionary of HTTP headers
        commonly used for authentication in API requests.

        Returns:
            dict: A dictionary containing HTTP headers with the 'Authorization' header set to
            'Bearer <bearer_token>'. This dictionary can be used in API requests for authentication
            purposes.
        """
        return {
            "token": f"{self.token}",
            "Content-Type": "application/json",
        }

    async def _process_response(self, response: ClientResponse) -> str:
        """
        Process an HTTP response and extract relevant information as a string.

        This function takes an HTTP response object as input and processes it to extract relevant information
        as a string. The extracted information may include data from the response body, headers, or other attributes.

        Args:
            response (ClientResponse): An HTTP response object containing the response data.

        Returns:
            str: A string representing the relevant information extracted from the response.
        """
        try:
            output = ""
            buffer = ""
            async for chunk in response.content.iter_chunked(1024):
                if chunk:
                    buffer += chunk.decode()
                    data, buffer = buffer.split("\0", 1)
                    data = json.loads(data)
                    text = data["text"].strip()
                    output = text
            return output
        
        except Exception as exception:
            print(
                f"An exception has occurred: {str(exception)}, {await response.text()}"
            )
            raise exception
