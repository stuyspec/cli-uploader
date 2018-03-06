// Package graphql provides a GraphQL client to the Spectator Rails API.
package graphql

import (
	"github.com/joho/godotenv"
	"github.com/shurcooL/graphql"
	"log"
	"context"
	"os"
)

var client *graphql.Client

func init() {
	err := godotenv.Load()
  if err != nil {
    log.Fatal("Error loading .env file in package graphql.")
  }

	apiEndpoint := "https://api.stuyspec.com"
	envApiEndpoint, found := os.LookupEnv("API_ENDPOINT")
	if found {
		apiEndpoint = envApiEndpoint
	}

	client = graphql.NewClient(apiEndpoint + "/graphql", nil)
}

func AllSections() {
	err := client.Query(context.Background(), &query, nil)
	if err != nil {
		log.Printf("GraphQL AllSectionsQuery failed. %v", err)
	}
	log.Printf("%v %T", query, query)
}
