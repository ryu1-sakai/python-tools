import argparse
import csv
import os
import sys
from dataclasses import dataclass
from itertools import islice

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

API_URL = 'https://api.github.com/graphql'

def create_graphql_client(github_access_token):
    transport = RequestsHTTPTransport(
        url=API_URL,
        headers={
            'Authorization': f'bearer {github_access_token}',
            'Content-Type': 'application/json',
        },
        verify=True,
        retries=3,
    )
    return Client(transport=transport, fetch_schema_from_transport=True)

def print_github_api_rate_limit_info(response):
    rate_limit = response['rateLimit']
    limit = rate_limit['limit']
    cost = rate_limit['cost']
    remaining = rate_limit['remaining']
    print(f"API Rate Limit: limit={limit} cost={cost} remaining={remaining}")

@dataclass
class PaginatedList[T]:
    elements: list[T]
    end_cursor: str
    has_next: bool

@dataclass
class PullRequest:
    number: int
    review_count: int

    @classmethod
    def from_graphql_node(cls, node):
        number = node['number']
        review_count = node['reviews']['totalCount']
        return PullRequest(number=number, review_count=review_count)

def get_pull_requests(gql_client, owner, name, status, after, size):
    query = gql(
        """
        query GetPullRequests($owner: String!, $name: String!, $after: String!, $size: Int!, $status: PullRequestState!) {
          repository(owner: $owner, name: $name) {
            pullRequests(first: $size, after: $after, states: [$status]) {
              nodes {
                number
                reviews {
                  totalCount
                }
              }
              pageInfo {
                endCursor
                hasNextPage
              }
            }
          }
          rateLimit {
            limit
            cost
            remaining
          }
        }
        """
    )
    variable_values = {
        'owner': owner,
        'name': name,
        'after': after,
        'size': size,
        'status': status,
    }
    response = gql_client.execute(query, variable_values = variable_values)
    print_github_api_rate_limit_info(response)
    nodes = response['repository']['pullRequests']['nodes']
    page_info = response['repository']['pullRequests']['pageInfo']
    return PaginatedList(
        elements=list(map(lambda n: PullRequest.from_graphql_node(n), nodes)),
        end_cursor=page_info['endCursor'],
        has_next=page_info['hasNextPage'],
    )

def iterate_pull_requests(gql_client, owner, name, status, after =''):
    page_size = 100
    while True:
        response = get_pull_requests(gql_client=gql_client, owner=owner, name=name, status=status, after=after, size=page_size)
        for pr in response.elements:
            yield pr
        if not response.has_next:
            break
        after=response.end_cursor

@dataclass
class ReviewComment:
    id: str
    path: str
    body: str

    @classmethod
    def from_graphql_node(cls, node):
        id = node['id']
        path = node['path']
        body = node['body']
        return ReviewComment(id=id, path=path, body=body)

def get_pull_request_review_comments(gql_client, owner, name, pr_number):
    query = gql(
        """
        query GetPullRequestReviewComments($owner: String!, $name: String!, $prNumber: Int!) {
          repository(owner: $owner, name: $name) {
            pullRequest(number: $prNumber) {
              reviews(first: 100) {
                nodes {
                  id
                  comments(first: 100) {
                    nodes {
                      id
                      path
                      body
                    }
                  }
                }
              }
            }
          }
          rateLimit {
            limit
            cost
            remaining
          }
        }
        """
    )
    variable_values = {
        'owner': owner,
        'name': name,
        'prNumber': pr_number,
    }
    response = gql_client.execute(query, variable_values = variable_values)
    print_github_api_rate_limit_info(response)
    review_nodes = response['repository']['pullRequest']['reviews']['nodes']
    comment_nodes = [cnode for rnode in review_nodes for cnode in rnode['comments']['nodes']]
    comments = map(lambda n: ReviewComment.from_graphql_node(n), comment_nodes)
    for comment in comments:
        yield comment

def iterate_pull_request_review_comments(gql_client, owner, name, status):
    pr_iter = iterate_pull_requests(gql_client=gql_client, owner=owner, name=name, status=status)
    reviewed_prs = filter(lambda pr: pr.review_count > 0, pr_iter)
    for pr in reviewed_prs:
        yield from get_pull_request_review_comments(gql_client=gql_client, owner=owner, name=name, pr_number=pr.number)

def download_pull_request_review_comments(gql_client, owner, name, output_file, extension = None, max_rows = None):
    print(f'Downloading PR comments from {owner}/{name} (max={max_rows})')
    review_comment_iter = iterate_pull_request_review_comments(gql_client=gql_client, owner=owner, name=name, status='MERGED')
    if extension:
        review_comment_iter = filter(lambda rc: rc.path.endswith(extension), review_comment_iter)
    if max_rows:
        review_comment_iter = islice(review_comment_iter, max_rows)
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for rc in review_comment_iter:
            row = [rc.path, rc.body]
            writer.writerow(row)

if __name__ == '__main__':
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print('ERROR: GITHUB_TOKEN is not available', file=sys.stderr)
        exit(1)
    client = create_graphql_client(github_token)

    parser = argparse.ArgumentParser(description='Download PR comments of GitHub repository')
    parser.add_argument('owner', type=str, help='repository owner')
    parser.add_argument('name', type=str, help='repository name')
    parser.add_argument('-o', '--output', type=str, help='output file path')
    parser.add_argument('-x', '--max', type=int, help='max comments to download')
    args = parser.parse_args()

    output = args.output if args.output else f'{args.owner}-{args.name}.csv'
    download_pull_request_review_comments(
        gql_client=client,
        owner=args.owner,
        name=args.name,
        extension='.kt',
        output_file=output,
        max_rows=args.max,
    )
