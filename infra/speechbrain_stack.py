from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    Duration
)
from constructs import Construct

class SpeechBrainStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create the Lambda function from the Docker image in the speechbrain directory
        speechbrain_lambda = _lambda.DockerImageFunction(
            self, 'SpeechBrainFunction',
            code=_lambda.DockerImageCode.from_image_asset('infra/speechbrain'),
            memory_size=2048,  # SpeechBrain needs some RAM to load ECAPA-TDNN
            timeout=Duration.seconds(30),
            architecture=_lambda.Architecture.X86_64,
        )

        # Create API Gateway in front of the Lambda
        api = apigw.LambdaRestApi(
            self, 'SpeechBrainApi',
            handler=speechbrain_lambda,
            proxy=True,
            binary_media_types=["audio/wav", "multipart/form-data"]
        )
