/*
 * Generated from saved assertion gaps.
 * framework=generic c test
 * language=c
 * filename=RQ15_chunk3_missing_test_1.c
 */

#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <est.h>
#include <curl/curl.h>
#include "curl_utils.h"
#include "test_utils.h"

static void rq15_chunk3_missing_test_1(void)
{
    LOG_FUNC_NM
    ;

    CURL *hnd = NULL;
    CURLcode res;
    long num_connects = 0;

    /* Initialize a single easy handle and enable TCP keepalive, allow reuse */
    hnd = curl_easy_init();
    assert(hnd != NULL);

    /* Target a local test server; the exact URL/port is provided by test harness in exemplars */
    curl_easy_setopt(hnd, CURLOPT_URL, "http://127.0.0.1:8080/");
    curl_easy_setopt(hnd, CURLOPT_VERBOSE, 0L);
    curl_easy_setopt(hnd, CURLOPT_TCP_KEEPALIVE, 1L);
    /* Allow connection reuse so HTTP/1.1 persistent connection may be used */
    curl_easy_setopt(hnd, CURLOPT_FORBID_REUSE, 0L);

    /* First request: should open a connection */
    res = curl_easy_perform(hnd);
    assert(res == CURLE_OK);

    /* Second request on the same handle: with HTTP/1.1 and reuse allowed this should reuse the connection */
    res = curl_easy_perform(hnd);
    assert(res == CURLE_OK);

    /* Query libcurl for number of distinct connections used; expect 1 if connection was reused */
    res = curl_easy_getinfo(hnd, CURLINFO_NUM_CONNECTS, &num_connects);
    assert(res == CURLE_OK);
    assert(num_connects == 1);

    curl_easy_cleanup(hnd);
}
