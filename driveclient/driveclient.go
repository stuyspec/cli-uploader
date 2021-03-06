// Package driveclient contains useful functions for creating and interacting
// with the Drive client API.
package driveclient

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"net/url"
	"os"
	"os/user"
	"path/filepath"

	"golang.org/x/net/context"
	"golang.org/x/oauth2"
	"golang.org/x/oauth2/google"
	"google.golang.org/api/drive/v3"

	"github.com/skratchdot/open-golang/open"
)

var driveService *drive.Service

func init() {
	ctx := context.Background()

	b, readErr := ioutil.ReadFile("client_secret.json")
	if readErr != nil {
		log.Fatalf("Unable to read client secret file: %v", readErr)
	}

	// If modifying these scopes, delete your previously saved credentials
	// at ~/.credentials/drive-go-stuy-spec-uploader.json. The DriveScope allows
	// us to view and manage the files in Drive.
	config, err := google.ConfigFromJSON(b, drive.DriveScope)
	if err != nil {
		log.Fatalf("Unable to parse client secret file to config: %v", err)
	}
	httpClient := getClient(ctx, config)

	var driveErr error
	driveService, driveErr = drive.New(httpClient)
	if driveErr != nil {
		log.Fatalf("Unable to retrieve drive Client %v", driveErr)
	}
}

// getClient uses a Context and Config to retrieve an auth Token
// then generate a Drive Client object. It returns the generated Client.
func getClient(ctx context.Context, config *oauth2.Config) *http.Client {
	cacheFile, err := tokenCacheFile()
	if err != nil {
		log.Fatalf("Unable to get path to cached credential file. %v", err)
	}
	tok, err := tokenFromFile(cacheFile)
	if err != nil {
		tok = getTokenFromWeb(config)
		saveToken(cacheFile, tok)
	}
	return config.Client(ctx, tok)
}

// getTokenFromWeb uses Config to request a Token to use with the Drive Client.
// It returns the retrieved Token.
func getTokenFromWeb(config *oauth2.Config) *oauth2.Token {
	authURL := config.AuthCodeURL("state-token", oauth2.AccessTypeOffline)
	open.Run(authURL) // opens authURL in default browser
	fmt.Printf("Type the authorization code: ")

	var code string
	if _, err := fmt.Scan(&code); err != nil {
		log.Fatalf("Unable to read authorization code %v", err)
	}

	tok, err := config.Exchange(oauth2.NoContext, code)
	if err != nil {
		log.Fatalf("Unable to retrieve token from web %v", err)
	}
	return tok
}

// tokenCacheFile generates credential file path/filename.
// It returns the generated credential path/filename.
func tokenCacheFile() (string, error) {
	usr, err := user.Current()
	if err != nil {
		return "", err
	}
	tokenCacheDir := filepath.Join(usr.HomeDir, ".credentials")
	os.MkdirAll(tokenCacheDir, 0700)
	return filepath.Join(tokenCacheDir,
		url.QueryEscape("drive-go-stuy-spec-uploader.json")), err
}

// tokenFromFile retrieves a Token from a given file path.
// It returns the retrieved Token and any read error encountered.
func tokenFromFile(file string) (*oauth2.Token, error) {
	f, err := os.Open(file)
	if err != nil {
		return nil, err
	}
	t := &oauth2.Token{}
	err = json.NewDecoder(f).Decode(t)
	defer f.Close()
	return t, err
}

// saveToken uses a file path to create a file and store the
// token in it.
func saveToken(file string, token *oauth2.Token) {
	fmt.Printf("Saving credential file to: %s\n", file)
	f, err := os.OpenFile(file, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0600)
	if err != nil {
		log.Fatalf("Unable to cache oauth token: %v", err)
	}
	defer f.Close()
	json.NewEncoder(f).Encode(token)
}

/*
"1cVqKaP6JVXHELBG2IEU5SEz1Xt9bLVZmrwtSLly_P7Y"
"[CLOSED] Issue9_News_BigSibConstitution",
"application/vnd.google-apps.document",
[]string{"1DSDSpkPIq_7R69BXO_pLwPKT-cxK0D8H"},
*/

// ScanDriveFiles reads metadata on all Drive files from the Drive client.
// It returns the DriveFiles.
func ScanDriveFiles() map[string]*drive.File {
	driveFiles := make(map[string]*drive.File)

	// Loop through pages of files
	var nextPageToken string
	for {
		query := driveService.Files.List().PageSize(100).
			Fields("nextPageToken, " +
				"files(id, name, parents, mimeType, webContentLink)")
		if len(nextPageToken) > 0 {
			query = query.PageToken(nextPageToken)
		}

		r, err := query.Do()
		if err != nil {
			log.Fatalf("Unable to retrieve files: %v", err)
			break
		}
		if r.NextPageToken == "" {
			break
		}

		for _, f := range r.Files {
			driveFiles[f.Id] = f
		}

		fmt.Printf("Scanned %d Drive files.\n", len(driveFiles))

		nextPageToken = r.NextPageToken
	}

	return driveFiles

}

// DownloadGoogleDoc downloads a Drive file by its ID.
// It returns the plain text of the Doc.
func DownloadGoogleDoc(fileID string) (text string) {
	res, err := driveService.Files.Export(fileID, "text/plain").Download()
	if err != nil {
		log.Fatalf("Unable to download file. %v", err)
	}

	if res.StatusCode == http.StatusOK {
		bodyBytes, readErr := ioutil.ReadAll(res.Body)
		if readErr != nil {
			log.Fatalf("Unable to read response body. %v", readErr)
		}
		text = string(bodyBytes)
	} else {
		log.Fatalf("Request failed. %v", res)
	}
	return
}
