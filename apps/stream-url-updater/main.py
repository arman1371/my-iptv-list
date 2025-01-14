import hydra
from omegaconf import DictConfig, ListConfig
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.firefox.webdriver import WebDriver


def get_driver(proxy: DictConfig) -> WebDriver:
    if not proxy.use:
        return webdriver.Firefox()
    else:
        options = webdriver.FirefoxOptions()
        options.proxy = Proxy(
            {
                "proxyType": ProxyType.MANUAL,
                "httpProxy": proxy.httpProxy,
                "sslProxy": proxy.sslProxy,
            }
        )
        return webdriver.Firefox(options=options)


def get_stream_link(proxy: DictConfig, url: str, xpath: str) -> str:
    driver = get_driver(proxy=proxy)
    driver.get(url=url)
    stream_link = driver.find_element(By.XPATH, xpath).get_attribute("src")
    driver.close()

    return stream_link


def generate_results(proxy: DictConfig, sources: ListConfig) -> list:
    results = []
    for source in sources:
        res = {"name": source.name}
        res["link"] = get_stream_link(proxy=proxy, url=source.url, xpath=source.xpath)
        results.append(res)

    return results


def create_output(channels: list) -> None:
    with open("irib.m3u8", "w") as file:
        file.write("#EXTM3U\n\n")

        for channel in channels:
            file.write(f"#EXTINF:-1,{channel['name']}\n")
            file.write(f"{channel['link']}\n\n")


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig) -> None:
    channels = generate_results(cfg.proxy, sources=cfg.sources)
    create_output(channels=channels)


if __name__ == "__main__":
    main()
